"""Telephony degradation — make clean 16 kHz audio sound like a real phone call.

Real bank calls are 8 kHz, band-limited (300-3400 Hz), G.711 µ-law companded,
and lossy. Models trained on clean audio collapse on this. Use this both to
AUGMENT training data (so the model learns telephony) and as a DEMO filter
("play the clone through a phone line — still caught").

scipy only (already a dependency). ponytail: G.711 µ-law + band-limit + optional
packet loss; add AMR/GSM codecs only if a bank's lines need them.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, lfilter, resample_poly

_PHONE_LOW, _PHONE_HIGH = 300.0, 3400.0  # standard telephone passband


def _bandlimit(x: np.ndarray, sr: int) -> np.ndarray:
    ny = sr / 2.0
    b, a = butter(4, [_PHONE_LOW / ny, _PHONE_HIGH / ny], btype="band")
    return lfilter(b, a, x).astype("float32")


def mu_law(x: np.ndarray, mu: int = 255) -> np.ndarray:
    """G.711 µ-law: companded, 8-bit quantised, expanded back."""
    x = np.clip(x, -1.0, 1.0)
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = np.round((y + 1) / 2 * mu) / mu * 2 - 1            # 8-bit quantise
    xr = np.sign(q) * (1.0 / mu) * ((1 + mu) ** np.abs(q) - 1)  # expand
    return xr.astype("float32")


def to_telephony(audio: np.ndarray, sr: int = 16000, packet_loss: float = 0.0) -> np.ndarray:
    """Degrade `audio` to telephony quality, returned at the original sample rate.

    packet_loss: fraction of 20 ms frames to drop (0..1), simulating a lossy line.
    """
    x = _bandlimit(audio.astype("float32"), sr)
    x8 = resample_poly(x, 8000, sr)            # to 8 kHz codec rate
    x8 = mu_law(x8)                            # G.711
    if packet_loss > 0:
        frame = max(1, int(0.02 * 8000))       # 20 ms
        for i in range(0, len(x8), frame):
            if np.random.rand() < packet_loss:
                x8[i:i + frame] = 0.0
    xr = resample_poly(x8, sr, 8000).astype("float32")  # back to original sr
    return xr[: len(audio)]


if __name__ == "__main__":
    # ponytail self-check: shape preserved, finite, energy collapses out of phone band.
    sr = 16000
    t = np.linspace(0, 1, sr, endpoint=False)
    clean = (0.5 * np.sin(2 * np.pi * 1000 * t) + 0.5 * np.sin(2 * np.pi * 6000 * t)).astype("float32")
    deg = to_telephony(clean, sr)
    assert deg.shape == clean.shape, "length must be preserved"
    assert np.all(np.isfinite(deg)), "no NaN/inf"
    # 6 kHz tone is above the 3.4 kHz phone band -> should be heavily attenuated.
    hi_clean = np.abs(np.fft.rfft(clean))[int(6000 / (sr / len(clean)))]
    hi_deg = np.abs(np.fft.rfft(deg))[int(6000 / (sr / len(deg)))]
    assert hi_deg < hi_clean * 0.2, "out-of-band energy should be removed"
    print("telephony self-check ok")
