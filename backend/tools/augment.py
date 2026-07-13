"""Acoustic augmentation for retraining a REVERB-ROBUST detector.

The deployed detectors nail clean audio but false-positive on live mic audio: the
culprit is room REVERBERATION (verified -- real speech in a room reads as fake, and
reverb even masks real clones). They were fine-tuned on clean/studio audio, so they
never learned that reverberant real speech is still real. The fix the research
converges on (RawBoost, Tak et al. 2022, ASVspoof winners) is to AUGMENT the
training set with the conditions seen at deployment -- reverb, noise, codecs -- and
retrain. This module produces that augmented set.

Apply to BOTH classes (real and clone) so the model learns reverb is channel, not
spoof. Feed the output into the existing training pipeline (PHASE-H-KAGGLE.md).

  python -m tools.augment --in train/real  --out train_aug/real  --per 3
  python -m tools.augment --in train/clone --out train_aug/clone --per 3

scipy/numpy only. Reuses ml/telephony.py for the phone-line condition.
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from ml.audio_utils import load_audio, SAMPLE_RATE
from ml.telephony import to_telephony


def synth_rir(rt60: float, sr: int = SAMPLE_RATE, seed: int | None = None) -> np.ndarray:
    """A synthetic room impulse response: direct path + a few early reflections +
    an exponentially-decaying diffuse tail (Schroeder model). rt60 in seconds sets
    the reverberation time (0.2 small room .. 0.9 hall). For best results ALSO mix
    in real measured RIRs (OpenSLR RIR/MUSAN) when you have them."""
    rng = np.random.default_rng(seed)
    n = int((rt60 * 1.2 + 0.05) * sr)
    t = np.arange(n) / sr
    ir = (rng.standard_normal(n) * np.exp(-6.9 * t / rt60)).astype(np.float32)  # -60 dB @ rt60
    ir[0] = 1.0
    for d, g in [(0.005, 0.6), (0.011, 0.45), (0.019, 0.35), (0.029, 0.28), (0.041, 0.2)]:
        j = int(d * sr)
        if j < n:
            ir[j] += g * rng.uniform(0.7, 1.3)
    return ir / (np.abs(ir).max() + 1e-9)


def add_reverb(x: np.ndarray, rt60: float, seed: int | None = None) -> np.ndarray:
    y = fftconvolve(x, synth_rir(rt60, seed=seed))[:len(x)]
    peak = np.abs(y).max()
    return (y / peak * np.abs(x).max()).astype(np.float32) if peak > 0 else x


def add_noise(x: np.ndarray, snr_db: float, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = np.mean(x ** 2) + 1e-12
    n = rng.standard_normal(len(x)).astype(np.float32)
    n *= np.sqrt(p / (10 ** (snr_db / 10)) / (np.mean(n ** 2) + 1e-12))
    return (x + n).astype(np.float32)


def random_chain(x: np.ndarray, seed: int) -> tuple[np.ndarray, str]:
    """One randomly-composed real-world condition: reverb, then maybe noise, then
    maybe a phone line. Returns (audio, tag) so filenames record what was applied."""
    rng = np.random.default_rng(seed)
    y, parts = x, []
    if rng.random() < 0.8:
        rt60 = float(rng.uniform(0.2, 0.8))
        y = add_reverb(y, rt60, seed=seed); parts.append(f"rev{int(rt60*100)}")
    if rng.random() < 0.6:
        snr = float(rng.uniform(5, 25))
        y = add_noise(y, snr, seed=seed + 1); parts.append(f"snr{int(snr)}")
    if rng.random() < 0.3:
        y = to_telephony(y, SAMPLE_RATE); parts.append("tel")
    return y, ("_".join(parts) or "clean")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True, help="folder of source .wav/.flac/.mp3")
    ap.add_argument("--out", required=True, help="folder to write augmented clips")
    ap.add_argument("--per", type=int, default=3, help="augmented variants per source clip")
    ap.add_argument("--keep-clean", action="store_true", help="also copy the original through")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    files = sorted(sum((glob.glob(os.path.join(args.src, e)) for e in ("*.wav", "*.flac", "*.mp3")), []))
    if not files:
        raise SystemExit(f"no audio in {args.src}")
    n = 0
    for f in files:
        x, _ = load_audio(f)
        stem = os.path.splitext(os.path.basename(f))[0]
        if args.keep_clean:
            sf.write(os.path.join(args.out, f"{stem}_clean.wav"), x, SAMPLE_RATE); n += 1
        for k in range(args.per):
            y, tag = random_chain(x, seed=hash((stem, k)) & 0xFFFF)
            sf.write(os.path.join(args.out, f"{stem}_{tag}_{k}.wav"), y, SAMPLE_RATE); n += 1
    print(f"wrote {n} augmented clips to {args.out} from {len(files)} sources")


def _selfcheck():
    # ponytail self-check: shapes preserved, reverb fills trailing silence.
    sr = SAMPLE_RATE
    t = np.linspace(0, 0.7, int(0.7 * sr), endpoint=False)
    burst = np.sin(2 * np.pi * 180 * t).astype(np.float32)
    x = np.concatenate([burst, np.zeros(int(0.3 * sr), np.float32)])  # 300 ms of true silence
    y = add_reverb(x, 0.5, seed=0)
    assert y.shape == x.shape, "length preserved"
    assert np.all(np.isfinite(y)), "finite"
    tail = slice(len(x) - int(0.2 * sr), len(x))                       # last 200 ms was silent
    assert np.mean(y[tail] ** 2) > 1e-9, "reverb tail should fill the trailing silence"
    assert add_noise(x, 10).shape == x.shape and np.all(np.isfinite(add_noise(x, 10)))
    print("augment self-check ok")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        _selfcheck()      # no args -> run the self-check
    else:
        main()            # args -> run the CLI
