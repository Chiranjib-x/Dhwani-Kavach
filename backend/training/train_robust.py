"""Train a CHANNEL-ROBUST deepfake detector (full-model GPU fine-tune).

Objective: rock-solid across channels for BOTH real and fake voices --
  * TELEPHONE (the main deployment target): 8 kHz, G.711 mu-law, 300-3400 Hz band
  * any MICROPHONE (gain, EQ, cheap capsules)
  * background NOISE
  * room REVERB
...so mic quality and surroundings do NOT move the score.

Architecture = the SOTA anti-spoofing family and EXACTLY what the app deploys:
wav2vec2-XLS-R-300M (multilingual -- good for Hindi/Indian voices) backbone +
W2VAASIST graph-attention head. The trained head drops straight into
ml/detector_v2.py (swap the safetensors). No new architecture to integrate.

Why full-model + diverse data: finetune_reverb.py PROVED a frozen-backbone,
narrow-data fit OVERFITS (flagged a real speaker as fake). Fix = unfreeze the
backbone (low LR) + train on MANY real sources and MANY fake generators +
augment every epoch, TELEPHONY-weighted. Validation is held out per-CONDITION
and per-SOURCE -- the anti-overfit gate.

Data layout -- just folders of audio, drop new files in ANY TIME:
  <root>/real/        public real speech   (Common Voice / VoxCeleb / LibriSpeech / In-The-Wild real)
  <root>/fake/        public + your spoofs (ASVspoof / Fake-or-Real / WaveFake / In-The-Wild fake / your clones)
  <root>/rir/         (optional) real room impulse responses (OpenSLR RIR) -- better than synth
  <root>/user_real/   (optional) HELD-OUT real recordings   (your friends' voices) -- VALIDATION ONLY
  <root>/user_fake/   (optional) HELD-OUT cloned recordings                        -- VALIDATION ONLY

user_real / user_fake are NEVER trained on -- each run reports their AUC on
channels never seen from them, the honest cross-source test the overfit run
failed. Put your friends' voices there. (--train-on-user folds them in later.)

Clips are loaded LAZILY via a DataLoader (scales to tens of thousands of files);
augmentation is applied on-the-fly per epoch, so 99 clones become hundreds of
varied views WITHOUT the friend-notebook's risky *50 literal duplication.

usage (Kaggle/GPU, out of the box via LibriSpeech+VITS bootstrap):
    PYTHONPATH=backend python -m training.train_robust --bootstrap --epochs 8
usage (your folders of diverse data):
    PYTHONPATH=backend python -m training.train_robust --data /kaggle/working/data --epochs 8
smoke (CPU, offline, ~30s -- tiny random model, no 1.2 GB download):
    PYTHONPATH=backend python -m training.train_robust --smoke
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from scipy.signal import fftconvolve

sys.path.insert(0, os.getcwd())
from ml import detector_v2
from ml.audio_utils import load_audio, repeat_pad, SAMPLE_RATE
from ml.vendor.codecfake_model import W2VAASIST
from ml.telephony import to_telephony
from tools.augment import add_reverb, add_noise

_OUT = os.path.join(os.path.dirname(__file__), "..", "models", "w2v2aasist_robust.safetensors")
_CUT = 64600
_AUDIO_EXT = ("*.wav", "*.flac", "*.mp3", "*.ogg", "*.m4a")
_VAL_CAP = 250    # clips/class used by the per-epoch gate (keeps eval cheap)


# --------------------------------------------------------------------------- #
# channel augmentation -- all fns share signature (x, rng, rirs).
# TELEPHONY-weighted: the phone line is the main deployment target.
# --------------------------------------------------------------------------- #
def _c_clean(x, rng, rirs):
    return x


def _c_telephony(x, rng, rirs):
    return to_telephony(x, SAMPLE_RATE, packet_loss=float(rng.choice([0.0, 0.0, 0.05, 0.1])))


def _c_reverb(x, rng, rirs):
    if rirs:  # real measured RIR generalizes better than synthetic
        ir = rirs[int(rng.integers(len(rirs)))]
        y = fftconvolve(x, ir)[:len(x)]
        peak = np.abs(y).max()
        return (y / peak * np.abs(x).max()).astype(np.float32) if peak > 0 else x
    return add_reverb(x, float(rng.uniform(0.25, 0.8)), seed=int(rng.integers(1 << 30)))


def _c_noise(x, rng, rirs):
    return add_noise(x, float(rng.uniform(5, 25)), seed=int(rng.integers(1 << 30)))


def _c_phone_room(x, rng, rirs):
    # realistic worst case: someone on a phone, in a room, with background noise
    return _c_telephony(_c_noise(_c_reverb(x, rng, rirs), rng, rirs), rng, rirs)


_CONDS = {"clean": _c_clean, "telephony": _c_telephony, "reverb": _c_reverb,
          "noise": _c_noise, "phone_room": _c_phone_room}
# training samples conditions with these weights (telephony dominates)
_TRAIN_W = {"telephony": 0.34, "phone_room": 0.24, "reverb": 0.14, "noise": 0.12, "clean": 0.16}
_VAL_CONDS = ["clean", "telephony", "reverb", "noise", "phone_room"]


def _prep(audio):
    """augmented waveform -> normalized (64600,) float32 tensor, matching detector_v2."""
    padded = repeat_pad(audio, length=_CUT).astype(np.float32)
    normed = (padded - padded.mean()) / np.sqrt(padded.var() + 1e-7)
    return torch.from_numpy(normed.astype(np.float32))


# --------------------------------------------------------------------------- #
# lazy dataset: load on demand, augment on-the-fly
# --------------------------------------------------------------------------- #
class ClipDS(Dataset):
    """items: list of (source, label) where source is a filepath OR a np.array.
    train=True -> random telephony-weighted channel per clip (fresh each epoch).
    cond set   -> fixed channel, deterministic per index (for the val gate)."""
    def __init__(self, items, train=False, cond=None, rirs=None):
        self.items, self.train, self.cond, self.rirs = items, train, cond, rirs
        self._names = list(_TRAIN_W); self._p = np.array([_TRAIN_W[n] for n in self._names])
        self._p /= self._p.sum()

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        src, y = self.items[i]
        try:
            x = load_audio(src)[0].astype(np.float32) if isinstance(src, str) else src.astype(np.float32)
        except Exception:
            x = np.zeros(_CUT, dtype=np.float32)
        if self.train:
            rng = np.random.default_rng()                       # fresh variety every epoch
            cond = self._names[rng.choice(len(self._names), p=self._p)]
        else:
            rng = np.random.default_rng(i)                      # stable val set
            cond = self.cond
        return _prep(_CONDS[cond](x, rng, self.rirs)), y


# --------------------------------------------------------------------------- #
# model: truncated XLS-R backbone (trainable) + warm-started W2VAASIST head
# --------------------------------------------------------------------------- #
class RobustDetector(nn.Module):
    def __init__(self, warm=True, n_layers=detector_v2._HIDDEN_LAYER, smoke=False):
        super().__init__()
        from transformers import Wav2Vec2Model, Wav2Vec2Config
        if smoke:  # offline tiny random backbone -- validates plumbing, no 1.2 GB download
            m = Wav2Vec2Model(Wav2Vec2Config(hidden_size=1024, num_hidden_layers=n_layers,
                                             num_attention_heads=16, intermediate_size=256))
        else:
            m = Wav2Vec2Model.from_pretrained(detector_v2._WAV2VEC2_BASE_ID)
        m.encoder.layers = nn.ModuleList(list(m.encoder.layers[:n_layers]))
        m.encoder.layer_norm = nn.Identity()
        m.config.output_hidden_states = False
        self.backbone = m
        self.head = W2VAASIST()
        if warm:
            from safetensors.torch import load_file
            st = os.path.join(os.path.dirname(__file__), "..", "models", "w2v2aasist_cotrain.safetensors")
            if os.path.exists(st):
                self.head.load_state_dict(load_file(st))
                print("warm-started head from cotrain checkpoint", flush=True)

    def forward(self, x):  # x: (B, 64600)
        h = self.backbone(x).last_hidden_state       # (B, T, 1024)
        w = h.unsqueeze(1).transpose(2, 3)           # (B, 1, 1024, T)
        _, logits = self.head(w)
        return logits


# --------------------------------------------------------------------------- #
# data discovery
# --------------------------------------------------------------------------- #
def _list_folder(path):
    return sorted(sum((glob.glob(os.path.join(path, e)) for e in _AUDIO_EXT), [])) if os.path.isdir(path) else []


def build_corpus(root, bootstrap, limit, smoke):
    rng = np.random.default_rng(0)
    if smoke:  # synthetic arrays: real=voiced tones, fake=harsh buzz -- exercises the code path
        t = np.linspace(0, 2.0, int(2.0 * SAMPLE_RATE), endpoint=False, dtype=np.float32)
        real = [(np.sin(2*np.pi*f*t) * (0.5 + 0.5*np.sin(2*np.pi*3*t)), 0) for f in (110, 140, 180, 220)]
        fake = [(np.sign(np.sin(2*np.pi*f*t)) * 0.3, 1) for f in (115, 150, 190, 230)]
        return {"train": real[:3] + fake[:3], "val": real[3:] + fake[3:], "user": [], "rir": None}

    real = [(p, 0) for p in _list_folder(os.path.join(root, "real"))] if root else []
    fake = [(p, 1) for p in _list_folder(os.path.join(root, "fake"))] if root else []
    rirs = [r for r in (load_audio(p)[0] for p in _list_folder(os.path.join(root, "rir")))] if root else []
    if (not real or not fake) and bootstrap:
        from training.finetune_reverb import build_corpus as _bc
        tr, vl = _bc()
        real += [(x, 0) for x, y in tr + vl if y == 0]
        fake += [(x, 1) for x, y in tr + vl if y == 1]
    if not real or not fake:
        raise SystemExit("need audio in <root>/real and <root>/fake (or pass --bootstrap)")
    if limit:
        real, fake = real[:limit], fake[:limit]

    def split(items):
        idx = rng.permutation(len(items)); n_val = max(1, int(len(items) * 0.15))
        return [items[i] for i in idx[n_val:]], [items[i] for i in idx[:n_val]]

    tr_r, vl_r = split(real); tr_f, vl_f = split(fake)
    train = tr_r + tr_f
    val = vl_r[:_VAL_CAP] + vl_f[:_VAL_CAP]
    user = ([(p, 0) for p in _list_folder(os.path.join(root, "user_real"))] +
            [(p, 1) for p in _list_folder(os.path.join(root, "user_fake"))]) if root else []
    print(f"corpus: train {len(tr_r)} real / {len(tr_f)} fake | val {len(vl_r[:_VAL_CAP])}+{len(vl_f[:_VAL_CAP])} | "
          f"rir {len(rirs)} | user(held-out) {len(user)}", flush=True)
    return {"train": train, "val": val, "user": user, "rir": rirs or None}


# --------------------------------------------------------------------------- #
# eval: rank-AUC per channel condition
# --------------------------------------------------------------------------- #
@torch.no_grad()
def _scores(model, items, cond, device, rirs, workers):
    if not items:
        return np.array([]), np.array([])
    dl = DataLoader(ClipDS(items, cond=cond, rirs=rirs), batch_size=16, num_workers=workers)
    model.eval(); probs, ys = [], []
    for xb, yb in dl:
        probs.extend(torch.softmax(model(xb.to(device)), 1)[:, 1].cpu().tolist()); ys.extend(yb.tolist())
    return np.array(probs), np.array(ys)


def _auc(probs, ys):
    pf, pr = probs[ys == 1], probs[ys == 0]
    if not len(pf) or not len(pr):
        return float("nan")
    return float((pf[:, None] > pr[None, :]).mean())


def evaluate(model, data, device, workers):
    res = {}
    for c in _VAL_CONDS:
        res[c] = _auc(*_scores(model, data["val"], c, device, data["rir"], workers))
    if data["user"]:
        for c in ("telephony", "phone_room"):
            res[f"USER_{c}"] = _auc(*_scores(model, data["user"], c, device, data["rir"], workers))
    return res


def _fmt(res):
    return " | ".join(f"{k}={v:.3f}" for k, v in res.items())


# --------------------------------------------------------------------------- #
# train
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="root with real/ fake/ [rir/ user_real/ user_fake/]")
    ap.add_argument("--bootstrap", action="store_true", help="fall back to LibriSpeech+VITS if folders empty")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr-head", type=float, default=1e-4)
    ap.add_argument("--lr-backbone", type=float, default=1e-5)  # low: don't wreck pretrained features
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=_OUT, help="where to save the best head (use a persistent dir on Kaggle)")
    ap.add_argument("--limit", type=int, default=None, help="cap clips per class (debug)")
    ap.add_argument("--train-on-user", action="store_true", help="fold user_* into TRAIN (default: val-only)")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = 0 if args.smoke else args.workers
    t0 = time.time()
    data = build_corpus(args.data, args.bootstrap, args.limit, args.smoke)
    if args.train_on_user and data["user"]:
        data["train"] += data["user"]; data["user"] = []

    model = RobustDetector(warm=not args.smoke, smoke=args.smoke).to(device)
    opt = torch.optim.AdamW([
        {"params": model.head.parameters(), "lr": args.lr_head},
        {"params": model.backbone.parameters(), "lr": args.lr_backbone},
    ], weight_decay=args.weight_decay)
    lossf = nn.CrossEntropyLoss()
    train_dl = DataLoader(ClipDS(data["train"], train=True, rirs=data["rir"]),
                          batch_size=args.batch, shuffle=True, num_workers=workers, drop_last=True)

    base = evaluate(model, data, device, workers)
    print(f"\nBASELINE  {_fmt(base)}\n", flush=True)
    min_base = min(v for k, v in base.items() if not k.startswith("USER"))

    from safetensors.torch import save_file
    best = -1.0
    for ep in range(args.epochs):
        model.train(); tot, nb = 0.0, 0
        for xb, yb in train_dl:
            logits = model(xb.to(device))
            loss = lossf(logits, yb.to(device))
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step(); tot += float(loss); nb += 1
        res = evaluate(model, data, device, workers)
        worst = min(v for k, v in res.items() if not k.startswith("USER"))
        flag = ""
        # anti-overfit gate: keep only if the WEAKEST channel beats baseline's weakest
        # AND clean doesn't regress. SAVE TO DISK immediately so a killed session
        # (Kaggle time limit) still leaves the best head on disk.
        if worst > best and worst >= min_base - 0.02 and res["clean"] >= base["clean"] - 0.02:
            best = worst
            save_file({k: v.detach().cpu().contiguous() for k, v in model.head.state_dict().items()}, args.out)
            flag = "  <- best (SAVED)"
        print(f"epoch {ep+1}/{args.epochs} loss={tot/max(nb,1):.3f} | {_fmt(res)} | worst={worst:.3f}{flag}", flush=True)

    if best < 0:
        print("\nno epoch beat baseline's weakest channel without regressing clean -- nothing saved.", flush=True)
        return
    print(f"\nBEST head saved -> {args.out}  (weakest channel {min_base:.3f} -> {best:.3f})", flush=True)
    print("Deploy: A/B via DHWANI_HEAD=<path> python -m eval.run on your real clips, then copy the head "
          "over models/w2v2aasist_cotrain.safetensors ONLY if it wins.", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
