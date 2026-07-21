"""Input-quality gate — decide whether a window is even worth a confident verdict.

The detector is only honest when its input resembles what it was trained on.
A too-quiet mic, a clipping mic, or a noisy/echoey room pushes the audio
out-of-distribution, and the model's score becomes unreliable in EITHER
direction -- it may pass a real caller OR (worse) wave through a played-back
deepfake as GREEN. Over-the-air replay is the textbook case: SSL detectors
collapse from ~2-3% EER to ~20-25% EER on re-recorded audio (Muller et al.,
Interspeech 2025). When we can't trust the score we must SAY so, not guess.

This module measures three cheap, robust DSP signals -- level, clipping, SNR --
and returns a plain-language reason the agent (or the caller) can act on
("move to a quieter place", "mic level too low"). detector.py turns a failing
verdict into the UNCERTAIN band instead of a false GREEN/RED.

numpy only. Thresholds are DEPLOYMENT KNOBS (real rooms/mics vary) -- tune
QUALITY_* against a few real recordings from the target handset/line.
"""
from __future__ import annotations

import numpy as np

# --- deployment knobs (tune on real target-channel audio) ------------------- #
SNR_MIN_DB = 12.0      # below this the room/line noise dominates -> unreliable
RMS_MIN = 0.006        # below this the caller is too quiet / mic gain too low
RMS_CLIP_FRAC = 0.01   # >1% of samples at full-scale -> clipping distortion
_EPS = 1e-10


def _segmental_snr_db(x: np.ndarray, sr: int) -> float:
    """Rough non-intrusive SNR: split 25 ms frame energies into a noise floor
    (quietest frames) and a speech level (active frames). Not perceptual MOS --
    just enough to tell "clean line" from "noisy room". Conservative (a fully
    gap-less clip reads a little low), which fails safe toward 'verify'."""
    n = len(x)
    if n < sr // 10:                       # <100 ms: nothing to judge
        return 0.0
    win = max(1, int(0.025 * sr))
    n_frames = n // win
    if n_frames < 4:
        return 0.0
    frames = x[: n_frames * win].reshape(n_frames, win)
    e = np.mean(frames.astype(np.float64) ** 2, axis=1) + _EPS
    noise = float(np.mean(e[e <= np.percentile(e, 10)]))   # quietest 10%
    speech = float(np.mean(e[e >= np.percentile(e, 50)]))  # active half
    if noise <= _EPS or speech <= noise:
        return 0.0
    return 10.0 * np.log10(speech / noise)


def assess(audio: np.ndarray, sr: int = 16000) -> dict:
    """Return an input-quality report for a mono float32 waveform.

    Keys: ok (bool), score (0-100, higher = cleaner), reason (why it failed,
    'ok' when it passed), and the raw metrics (snr_db, rms, clip_frac) for the
    UI / logs. Empty or silent input -> ok False, 'no audio'."""
    x = np.asarray(audio, dtype=np.float32).ravel()
    if x.size == 0:
        return {"ok": False, "score": 0, "reason": "no audio",
                "snr_db": 0.0, "rms": 0.0, "clip_frac": 0.0}

    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    clip_frac = float(np.mean(np.abs(x) >= 0.99))
    snr_db = float(_segmental_snr_db(x, sr))

    # First failing check wins the message (the caller can only fix one thing at
    # a time; lead with the most actionable). Silence-ish first, then clipping,
    # then noise. Order matters: a dead-quiet clip also reads low SNR.
    if rms < RMS_MIN:
        reason = "mic level too low — speak up or move closer to the mic"
        ok = False
    elif clip_frac > RMS_CLIP_FRAC:
        reason = "audio is clipping — lower the mic/input gain"
        ok = False
    elif snr_db < SNR_MIN_DB:
        reason = "too much background noise — move to a quieter place"
        ok = False
    else:
        reason = "ok"
        ok = True

    # Composite 0-100 for the UI meter: SNR-dominated, knocked down by clipping
    # and low level so one clean number tracks "how trustworthy is this input".
    snr_component = float(np.clip(snr_db / 30.0, 0.0, 1.0))          # 0 dB..30 dB
    level_component = float(np.clip(rms / (RMS_MIN * 4), 0.0, 1.0))  # up to 4x floor
    clip_penalty = float(np.clip(clip_frac / 0.05, 0.0, 1.0))        # 5% clip = 0
    score = int(round(100 * (0.7 * snr_component + 0.3 * level_component) * (1.0 - clip_penalty)))

    return {"ok": ok, "score": score, "reason": reason,
            "snr_db": round(snr_db, 1), "rms": round(rms, 4), "clip_frac": round(clip_frac, 4)}


if __name__ == "__main__":
    # Self-check: clean speech-like passes; silence/quiet/clipping/noise fail
    # with the RIGHT reason (this is a money/security path — the abstain call
    # must not silently invert).
    sr = 16000
    rng = np.random.default_rng(0)
    t = np.arange(2 * sr) / sr

    # clean-ish: voiced tone at a healthy level + a low noise floor + pauses
    voiced = 0.3 * np.sin(2 * np.pi * 160 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))
    voiced[: sr // 2] = 0.0                      # a real pause -> a noise-floor sample
    clean = (voiced + 0.002 * rng.standard_normal(len(t))).astype(np.float32)
    r = assess(clean, sr)
    assert r["ok"], f"clean audio should pass, got {r}"

    # dead quiet
    quiet = (0.001 * rng.standard_normal(sr)).astype(np.float32)
    r = assess(quiet, sr)
    assert not r["ok"] and "level" in r["reason"], f"quiet should flag level, got {r}"

    # clipping
    clipped = np.clip(3.0 * np.sin(2 * np.pi * 200 * t), -1.0, 1.0).astype(np.float32)
    r = assess(clipped, sr)
    assert not r["ok"] and "clip" in r["reason"], f"clipping should flag, got {r}"

    # loud but buried in noise (low SNR, no clean pauses)
    noisy = (0.25 * np.sin(2 * np.pi * 160 * t) + 0.25 * rng.standard_normal(len(t))).astype(np.float32)
    r = assess(noisy, sr)
    assert not r["ok"] and "noise" in r["reason"], f"noisy should flag noise, got {r}"

    # empty
    assert not assess(np.array([], dtype=np.float32))["ok"]
    print("quality self-check ok")
