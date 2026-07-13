"""Fine-tune the W2VAASIST head for REVERB robustness (frozen backbone, CPU-OK).

Root cause of the mic false-positives (see dhwani-reverb-robustness): the head was
trained on clean audio, so reverberant real speech reads as fake. Fix = show it
reverberant REAL and reverberant FAKE during training so it learns reverb is a
channel effect, not a spoof cue.

Pipeline: build corpus (LibriSpeech real + VITS fake) -> augment both classes with
reverb/noise -> freeze the (truncated) XLS-R backbone and cache its features once ->
warm-start fine-tune ONLY the W2VAASIST head -> validate on held-out CLEAN and
REVERB -> save models/w2v2aasist_reverb.safetensors ONLY if it beats the current
head on the reverb set without losing clean accuracy.

usage: PYTHONPATH=backend python -m training.finetune_reverb
"""
from __future__ import annotations

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
from tools.augment import add_reverb, add_noise

_OUT = os.path.join(os.path.dirname(__file__), "..", "models", "w2v2aasist_reverb.safetensors")
_N_REAL = 60          # LibriSpeech clips for the real class
_N_FAKE = 60          # VITS clips for the fake class
_VAL_FRAC = 0.25
_EPOCHS = 6
_LR = 5e-5
_rng = np.random.default_rng(0)


def _znorm(x):
    return ((x - x.mean()) / np.sqrt(x.var() + 1e-7)).astype(np.float32)


def _reverb(x):
    return add_reverb(x, float(_rng.uniform(0.3, 0.7)), seed=int(_rng.integers(1 << 30)))


def _noisy(x):
    return add_noise(x, float(_rng.uniform(8, 20)), seed=int(_rng.integers(1 << 30)))


# ---- data ----------------------------------------------------------------
def build_corpus():
    """Return (train_clips, val_clips) as lists of (audio_np, label). label 1=fake."""
    from datasets import load_dataset
    import librosa
    print("loading LibriSpeech (real) ...", flush=True)
    ds = load_dataset("hf-internal-testing/librispeech_asr_dummy", "clean", split="validation")
    reals, texts = [], []
    for i in range(min(_N_REAL, len(ds))):
        a = ds[i]["audio"]
        x = np.asarray(a["array"], dtype=np.float32)
        if a["sampling_rate"] != SAMPLE_RATE:
            x = librosa.resample(x, orig_sr=a["sampling_rate"], target_sr=SAMPLE_RATE)
        reals.append(x); texts.append(ds[i]["text"])

    print("synthesizing VITS (fake) ...", flush=True)
    from transformers import VitsModel, AutoTokenizer
    vm = VitsModel.from_pretrained("facebook/mms-tts-eng").eval()
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-eng")
    fakes = []
    for i in range(min(_N_FAKE, len(texts))):
        inp = tok(texts[i].lower(), return_tensors="pt")
        with torch.no_grad():
            w = vm(**inp).waveform[0].numpy().astype(np.float32)
        if vm.config.sampling_rate != SAMPLE_RATE:
            w = librosa.resample(w, orig_sr=vm.config.sampling_rate, target_sr=SAMPLE_RATE)
        fakes.append(w)

    items = [(x, 0) for x in reals] + [(x, 1) for x in fakes]
    idx = _rng.permutation(len(items))
    n_val = int(len(items) * _VAL_FRAC)
    val = [items[i] for i in idx[:n_val]]
    train = [items[i] for i in idx[n_val:]]
    print(f"corpus: {len(train)} train, {len(val)} val", flush=True)
    return train, val


# ---- features (frozen backbone) ------------------------------------------
def _feat(audio):
    """Truncated XLS-R last_hidden_state for one clip -> (1024, T) float32."""
    x = torch.from_numpy(_znorm(repeat_pad(audio, length=64600))).unsqueeze(0)
    with torch.no_grad():
        h = detector_v2._get_backbone()(x).last_hidden_state  # (1, T, 1024)
    return h[0].transpose(0, 1).contiguous().numpy().astype(np.float32)  # (1024, T)


def featurize(clips, variants):
    """clips: list of (audio,label). variants: list of fns applied to each clip
    (identity for clean). Returns (X list of (1024,T), y array)."""
    X, y = [], []
    for k, (audio, label) in enumerate(clips):
        for fn in variants:
            X.append(_feat(fn(audio))); y.append(label)
        if (k + 1) % 20 == 0:
            print(f"  featurized {k+1}/{len(clips)} clips x{len(variants)}", flush=True)
    return X, np.array(y, dtype=np.int64)


def _batch(X, idx):
    # stack (1024,T) -> (B,1,1024,T)
    t = torch.from_numpy(np.stack([X[i] for i in idx]))  # (B,1024,T)
    return t.unsqueeze(1)


# ---- head -----------------------------------------------------------------
def load_head(warm=True):
    m = W2VAASIST()
    if warm:
        from safetensors.torch import load_file
        st = os.path.join(os.path.dirname(__file__), "..", "models", "w2v2aasist_cotrain.safetensors")
        if os.path.exists(st):
            m.load_state_dict(load_file(st)); print("warm-started from cotrain head", flush=True)
    return m


@torch.no_grad()
def evaluate(head, X, y):
    head.eval()
    probs = []
    for i in range(0, len(X), 16):
        _, logits = head(_batch(X, list(range(i, min(i + 16, len(X))))))
        probs.extend(torch.softmax(logits, 1)[:, 1].tolist())
    probs = np.array(probs); yy = np.array(y)
    # EER-agnostic summary: AUC + accuracy at 0.5
    fake, real = probs[yy == 1], probs[yy == 0]
    auc = float(np.mean([ (f > real).mean() for f in fake ])) if len(fake) and len(real) else float("nan")
    acc = float(((probs >= 0.5).astype(int) == yy).mean())
    return auc, acc, probs


def main():
    t0 = time.time()
    train, val = build_corpus()

    print("featurizing train (clean + reverb + noise) ...", flush=True)
    Xtr, ytr = featurize(train, [lambda a: a, _reverb, _noisy])
    print("featurizing val: clean and reverb held-out sets ...", flush=True)
    Xv_clean, yv_clean = featurize(val, [lambda a: a])
    Xv_rev, yv_rev = featurize(val, [_reverb])

    head = load_head(warm=True)
    old_rev = evaluate(head, Xv_rev, yv_rev)
    old_clean = evaluate(head, Xv_clean, yv_clean)
    print(f"\nBEFORE  clean AUC={old_clean[0]:.3f} acc={old_clean[1]:.2f} | "
          f"reverb AUC={old_rev[0]:.3f} acc={old_rev[1]:.2f}\n", flush=True)

    opt = torch.optim.Adam(head.parameters(), lr=_LR)
    lossf = nn.CrossEntropyLoss()
    yt = torch.from_numpy(ytr)
    best, best_state = -1.0, None
    for ep in range(_EPOCHS):
        head.train()
        order = _rng.permutation(len(Xtr))
        tot = 0.0
        for i in range(0, len(order), 16):
            idx = list(order[i:i + 16])
            _, logits = head(_batch(Xtr, idx))
            loss = lossf(logits, yt[idx])
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss) * len(idx)
        ca = evaluate(head, Xv_clean, yv_clean)
        ra = evaluate(head, Xv_rev, yv_rev)
        score = ca[0] + ra[0]  # reward BOTH clean and reverb AUC
        flag = ""
        if score > best and ca[0] >= old_clean[0] - 0.03:   # never regress clean much
            best, best_state = score, {k: v.detach().clone() for k, v in head.state_dict().items()}
            flag = "  <- best"
        print(f"epoch {ep+1}/{_EPOCHS} loss={tot/len(Xtr):.3f} | "
              f"clean AUC={ca[0]:.3f} acc={ca[1]:.2f} | reverb AUC={ra[0]:.3f} acc={ra[1]:.2f}{flag}", flush=True)

    if best_state is None:
        print("\nno epoch improved reverb without hurting clean -- NOT saving.", flush=True)
        return
    head.load_state_dict(best_state)
    fin_clean = evaluate(head, Xv_clean, yv_clean)
    fin_rev = evaluate(head, Xv_rev, yv_rev)
    print(f"\nAFTER   clean AUC={fin_clean[0]:.3f} acc={fin_clean[1]:.2f} | "
          f"reverb AUC={fin_rev[0]:.3f} acc={fin_rev[1]:.2f}", flush=True)
    print(f"reverb AUC {old_rev[0]:.3f} -> {fin_rev[0]:.3f}  (Δ{fin_rev[0]-old_rev[0]:+.3f})", flush=True)

    if fin_rev[0] > old_rev[0] + 0.02:
        from safetensors.torch import save_file
        save_file({k: v.contiguous() for k, v in head.state_dict().items()}, _OUT)
        print(f"\nSAVED reverb-robust head -> {_OUT}", flush=True)
    else:
        print("\nreverb not improved enough -- NOT saving (keeping current head).", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
