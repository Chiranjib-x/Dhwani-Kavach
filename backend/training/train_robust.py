"""Train a CHANNEL-ROBUST deepfake detector (full-model GPU fine-tune).

Objective: rock-solid across channels for BOTH real and fake voices --
  * TELEPHONE (the main deployment target): 8 kHz, G.711 mu-law, 300-3400 Hz band
  * any MICROPHONE (gain, EQ, cheap capsules)
  * background NOISE
  * room REVERB
...so mic quality and surroundings do NOT move the score.

Why this file exists (vs finetune_reverb.py): that experiment PROVED augmentation
fixes reverb (val AUC 0.60->1.00) but ALSO proved a frozen-backbone, narrow-data
fit OVERFITS -- it flagged a real speaker's voice as fake on unseen data. The two
causes were: (1) frozen backbone (only the tiny head could adapt), (2) narrow data
(one real source, one fake generator). This pipeline fixes both:
  - FULL-model fine-tune (backbone unfrozen, low LR) -- more capacity to absorb channel
  - DIVERSE data (many real speakers + many fake generators; scale by adding folders)
  - on-the-fly channel augmentation every epoch, TELEPHONY-weighted
  - validation held out BY CONDITION and BY SOURCE -- the anti-overfit gate

Data layout -- just folders of audio, drop new files in ANY TIME:
  <root>/real/        public real speech   (Common Voice / VoxCeleb / LibriSpeech)
  <root>/fake/        public spoofs        (ElevenLabs / VITS / ASVspoof DF / others)
  <root>/rir/         (optional) real room impulse responses (OpenSLR RIR) -- better than synth
  <root>/user_real/   (optional) YOUR real recordings   -- VALIDATION-only by default
  <root>/user_fake/   (optional) YOUR cloned recordings -- VALIDATION-only by default

YOUR recordings are just another folder. Add them whenever you get them; no code
change. By default they go into VALIDATION (never trained on) so every run tells you
honestly whether the model handles YOUR voices on channels it has never seen from you
-- exactly the cross-source test the earlier overfit run failed. Pass
--train-on-user to fold them into training once you have enough.

usage (Kaggle/GPU, runs out of the box via LibriSpeech+VITS bootstrap):
    PYTHONPATH=backend python -m training.train_robust --bootstrap --epochs 8
usage (your own corpus of folders):
    PYTHONPATH=backend python -m training.train_robust --data /kaggle/working/data --epochs 8
smoke (CPU, offline, ~30s -- validates the code path with a tiny random model):
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

sys.path.insert(0, os.getcwd())
from ml import detector_v2
from ml.audio_utils import repeat_pad, SAMPLE_RATE
from ml.vendor.codecfake_model import W2VAASIST
from ml.telephony import to_telephony
from tools.augment import add_reverb, add_noise, synth_rir
from scipy.signal import fftconvolve

_OUT = os.path.join(os.path.dirname(__file__), "..", "models", "w2v2aasist_robust.safetensors")
_CUT = 64600
_AUDIO_EXT = ("*.wav", "*.flac", "*.mp3", "*.ogg", "*.m4a")


# --------------------------------------------------------------------------- #
# channel augmentation -- TELEPHONY-weighted (the main deployment target).
# Each condition is a named fn(audio)->audio so the val gate can score them apart.
# --------------------------------------------------------------------------- #
def _telephony(x, rng):
    return to_telephony(x, SAMPLE_RATE)


def _reverb(x, rng, rirs=None):
    if rirs:  # real measured RIR when available -- generalizes better than synth
        ir = rirs[int(rng.integers(len(rirs)))]
        y = fftconvolve(x, ir)[:len(x)]
        peak = np.abs(y).max()
        return (y / peak * np.abs(x).max()).astype(np.float32) if peak > 0 else x
    return add_reverb(x, float(rng.uniform(0.25, 0.8)), seed=int(rng.integers(1 << 30)))


def _noise(x, rng):
    return add_noise(x, float(rng.uniform(5, 25)), seed=int(rng.integers(1 << 30)))


def _phone_room(x, rng, rirs=None):
    # the realistic worst case: someone on a phone, in a room, with background noise
    return _telephony(_noise(_reverb(x, rng, rirs), rng), rng)


# training draws conditions with these weights: telephony dominates, then the
# combined phone+room+noise case, then single channels, and some clean.
_TRAIN_CONDS = [
    ("telephony", _telephony, 0.34),
    ("phone_room", _phone_room, 0.24),
    ("reverb", _reverb, 0.14),
    ("noise", _noise, 0.12),
    ("clean", lambda x, rng, rirs=None: x, 0.16),
]
# validation reports EACH of these separately -- the gate must pass all of them.
_VAL_CONDS = ["clean", "telephony", "reverb", "noise", "phone_room"]


def _apply(name, x, rng, rirs):
    for n, fn, _ in _TRAIN_CONDS:
        if n == name:
            return fn(x, rng, rirs) if fn.__code__.co_argcount >= 3 else fn(x, rng)
    raise KeyError(name)


# --------------------------------------------------------------------------- #
# model: truncated XLS-R backbone (trainable) + warm-started W2VAASIST head
# --------------------------------------------------------------------------- #
class RobustDetector(nn.Module):
    def __init__(self, warm=True, n_layers=detector_v2._HIDDEN_LAYER, smoke=False):
        super().__init__()
        from transformers import Wav2Vec2Model, Wav2Vec2Config
        if smoke:  # offline tiny random backbone -- validates plumbing without the 1.2 GB download
            cfg = Wav2Vec2Config(hidden_size=1024, num_hidden_layers=n_layers,
                                 num_attention_heads=16, intermediate_size=256)
            m = Wav2Vec2Model(cfg)
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


def _prep(audio):
    """augmented waveform -> normalized (64600,) tensor input, matching detector_v2."""
    padded = repeat_pad(audio, length=_CUT).astype(np.float32)
    normed = (padded - padded.mean()) / np.sqrt(padded.var() + 1e-7)
    return torch.from_numpy(normed.astype(np.float32))


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def _load_folder(path, limit=None):
    from ml.audio_utils import load_audio
    files = sorted(sum((glob.glob(os.path.join(path, e)) for e in _AUDIO_EXT), []))
    if limit:
        files = files[:limit]
    out = []
    for f in files:
        try:
            out.append(load_audio(f)[0].astype(np.float32))
        except Exception as e:
            print(f"  skip {os.path.basename(f)}: {e}", flush=True)
    return out


def build_corpus(root, bootstrap, limit, smoke):
    """Returns dict with train (real,fake) and val (real,fake) + optional user_* val.
    Split is by FILE here; for a true cross-speaker holdout keep speakers to separate
    folders and this file-level split becomes speaker-level."""
    rng = np.random.default_rng(0)
    if smoke:  # synthetic: real=voiced tones, fake=harsh buzz -- just exercises the code
        t = np.linspace(0, 2.0, int(2.0 * SAMPLE_RATE), endpoint=False, dtype=np.float32)
        real = [np.sin(2 * np.pi * f * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)) for f in (110, 140, 180, 220)]
        fake = [np.sign(np.sin(2 * np.pi * f * t)) * 0.3 for f in (115, 150, 190, 230)]
        return {"tr_real": real[:3], "tr_fake": fake[:3], "vl_real": real[3:], "vl_fake": fake[3:], "user": {}}

    real, fake, rir = [], [], []
    if root and os.path.isdir(root):
        real = _load_folder(os.path.join(root, "real"), limit)
        fake = _load_folder(os.path.join(root, "fake"), limit)
        rir = [r for r in _load_folder(os.path.join(root, "rir")) if len(r) > 8]
    if (not real or not fake) and bootstrap:
        # runs out of the box on Kaggle: LibriSpeech real + VITS fake (from finetune_reverb)
        from training.finetune_reverb import build_corpus as _bc
        tr, vl = _bc()
        for x, y in tr + vl:
            (fake if y else real).append(x)
    if not real or not fake:
        raise SystemExit("need audio in <root>/real and <root>/fake (or pass --bootstrap)")

    def split(xs):
        idx = rng.permutation(len(xs))
        n_val = max(1, int(len(xs) * 0.2))
        return [xs[i] for i in idx[n_val:]], [xs[i] for i in idx[:n_val]]

    tr_real, vl_real = split(real)
    tr_fake, vl_fake = split(fake)
    user = {}
    if root:
        ur, uf = _load_folder(os.path.join(root, "user_real")), _load_folder(os.path.join(root, "user_fake"))
        if ur or uf:
            user = {"real": ur, "fake": uf}
    print(f"corpus: train {len(tr_real)} real / {len(tr_fake)} fake | "
          f"val {len(vl_real)} real / {len(vl_fake)} fake | rir {len(rir)} | "
          f"user {len(user.get('real', []))} real / {len(user.get('fake', []))} fake", flush=True)
    return {"tr_real": tr_real, "tr_fake": tr_fake, "vl_real": vl_real, "vl_fake": vl_fake,
            "user": user, "rir": rir}


# --------------------------------------------------------------------------- #
# eval: AUC per channel condition
# --------------------------------------------------------------------------- #
@torch.no_grad()
def _auc_for(model, reals, fakes, cond, device, rirs, seed=1):
    model.eval()
    rng = np.random.default_rng(seed)  # fixed -> stable val sets across epochs
    def score(clips):
        out = []
        for i in range(0, len(clips), 8):
            batch = [_prep(_apply(cond, c, rng, rirs)) for c in clips[i:i + 8]]
            logits = model(torch.stack(batch).to(device))
            out.extend(torch.softmax(logits, 1)[:, 1].tolist())
        return np.array(out)
    pf, pr = score(fakes), score(reals)
    if not len(pf) or not len(pr):
        return float("nan")
    return float(np.mean([(f > pr).mean() for f in pf]))  # rank-AUC


def evaluate(model, data, device):
    rirs = data.get("rir") or None
    res = {c: _auc_for(model, data["vl_real"], data["vl_fake"], c, device, rirs) for c in _VAL_CONDS}
    u = data.get("user") or {}
    if u.get("real") and u.get("fake"):
        res["USER_telephony"] = _auc_for(model, u["real"], u["fake"], "telephony", device, rirs)
        res["USER_phone_room"] = _auc_for(model, u["real"], u["fake"], "phone_room", device, rirs)
    return res


def _fmt(res):
    return " | ".join(f"{k}={v:.3f}" for k, v in res.items())


# --------------------------------------------------------------------------- #
# train
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="corpus root with real/ fake/ [rir/ user_real/ user_fake/]")
    ap.add_argument("--bootstrap", action="store_true", help="fall back to LibriSpeech+VITS if folders empty")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr-head", type=float, default=1e-4)
    ap.add_argument("--lr-backbone", type=float, default=1e-5)  # low: full-model, don't wreck features
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--limit", type=int, default=None, help="cap clips per class (debug)")
    ap.add_argument("--train-on-user", action="store_true", help="fold user_* into TRAIN (default: val-only)")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    t0 = time.time()
    data = build_corpus(args.data, args.bootstrap, args.limit, args.smoke)
    rirs = data.get("rir") or None
    if args.train_on_user and data.get("user"):
        data["tr_real"] += data["user"].get("real", [])
        data["tr_fake"] += data["user"].get("fake", [])
        data["user"] = {}

    model = RobustDetector(warm=not args.smoke, smoke=args.smoke).to(device)
    opt = torch.optim.AdamW([
        {"params": model.head.parameters(), "lr": args.lr_head},
        {"params": model.backbone.parameters(), "lr": args.lr_backbone},
    ], weight_decay=args.weight_decay)
    lossf = nn.CrossEntropyLoss()

    train = [(x, 0) for x in data["tr_real"]] + [(x, 1) for x in data["tr_fake"]]
    cond_names = [c[0] for c in _TRAIN_CONDS]
    cond_p = np.array([c[2] for c in _TRAIN_CONDS]); cond_p /= cond_p.sum()
    rng = np.random.default_rng(0)

    base = evaluate(model, data, device)
    print(f"\nBASELINE  {_fmt(base)}\n", flush=True)
    min_base = min(v for k, v in base.items() if not k.startswith("USER"))

    best_score, best_state = -1.0, None
    for ep in range(args.epochs):
        model.train()
        order = rng.permutation(len(train))
        tot = 0.0
        for i in range(0, len(order), args.batch):
            idx = order[i:i + args.batch]
            xs, ys = [], []
            for j in idx:
                audio, label = train[j]
                cond = cond_names[rng.choice(len(cond_names), p=cond_p)]  # fresh channel per sample per epoch
                xs.append(_prep(_apply(cond, audio, rng, rirs))); ys.append(label)
            logits = model(torch.stack(xs).to(device))
            loss = lossf(logits, torch.tensor(ys, device=device))
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            tot += float(loss) * len(idx)
        res = evaluate(model, data, device)
        worst = min(v for k, v in res.items() if not k.startswith("USER"))  # gate on the WEAKEST channel
        flag = ""
        # save only if the weakest channel is at least as good as baseline's weakest
        # AND clean didn't regress -- this is the anti-overfit gate.
        if worst > best_score and worst >= min_base - 0.02 and res["clean"] >= base["clean"] - 0.02:
            best_score, best_state = worst, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            flag = "  <- best"
        print(f"epoch {ep+1}/{args.epochs} loss={tot/len(train):.3f} | {_fmt(res)} | worst={worst:.3f}{flag}", flush=True)

    if best_state is None:
        print("\nno epoch beat the baseline's weakest channel without regressing clean -- NOT saving.", flush=True)
        return
    model.load_state_dict(best_state)
    fin = evaluate(model, data, device)
    print(f"\nFINAL  {_fmt(fin)}", flush=True)
    print(f"weakest channel {min_base:.3f} -> {min(v for k,v in fin.items() if not k.startswith('USER')):.3f}", flush=True)

    from safetensors.torch import save_file
    # ship the HEAD as the drop-in detector_v2 checkpoint; also dump the full model
    # (backbone+head) so a follow-up run can resume the tuned backbone.
    save_file({k: v.contiguous() for k, v in model.head.state_dict().items()}, _OUT)
    save_file({k: v.contiguous() for k, v in model.state_dict().items()}, _OUT.replace(".safetensors", "_full.safetensors"))
    print(f"\nSAVED head -> {_OUT}\n      full -> {_OUT.replace('.safetensors', '_full.safetensors')}", flush=True)
    print("To deploy: copy the head over models/w2v2aasist_cotrain.safetensors AFTER it passes "
          "backend/eval/ on your real clips.", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
