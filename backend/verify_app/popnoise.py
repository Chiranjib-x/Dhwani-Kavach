"""Near-field / pop-noise liveness — the physical defense against a clone played
through a loudspeaker (the over-the-air replay attack).

A live mouth close to the mic pushes AIR on plosives (p/b/t/k) and between words
(breath). That airflow makes low-frequency "pop noise" a loudspeaker CANNOT
reproduce — a speaker moves a diaphragm to make pressure, it doesn't blow air.
So this flags a played-back clone regardless of how good the clone is, which
synthesis detection (the CM) cannot. Peer-reviewed: POCO corpus; CQT / wavelet
pop-noise features (EUSIPCO 2021/2022; Speech Comm. 2023).

Pure DSP (librosa), no training. It returns interpretable features + a combined
score; the ENFORCED threshold is set by scripts/calibrate_popnoise.py on real
live-vs-replay captures (see MASTER-PLAN / the KEEP_AUDIO capture path). Until
calibrated it is REPORT-ONLY (config.POP_ENFORCE) so it can't reject genuine users.

Channel caveat: pop noise is sub-~300 Hz, so a narrowband PSTN call (300-3400 Hz)
filters it out. This works on full-band app/browser/VoIP audio. Capture MUST be
raw (no noiseSuppression/echoCancellation) or the browser strips the signal.
"""
from __future__ import annotations

import numpy as np

SR = 16000
_N_FFT = 2048
_HOP = 256
_EPS = 1e-12


def analyze(wav16k: np.ndarray) -> dict:
    """Raw pop-noise / near-field features for a mono float32 waveform @16 kHz.

    Returns a dict of channel/proximity cues that separate a live near-field
    voice from a loudspeaker replay:
      low_ratio  : energy 20-200 Hz relative to speech band (proximity + breath;
                   phone speakers roll this off hard)
      pop_rate   : fraction of voiced frames with a low-band TRANSIENT burst
                   (a plosive/breath pop) — the core live cue
      high_ratio : energy 3.4-8 kHz vs speech band (replay chains lose the top)
      flatness   : mean spectral flatness (loudspeaker+room adds coloration)
    """
    x = np.ascontiguousarray(wav16k, dtype=np.float32).ravel()
    if x.size < SR // 4:                       # <0.25 s: nothing to judge
        return {"low_ratio": 0.0, "pop_rate": 0.0, "high_ratio": 0.0, "flatness": 0.0, "n": 0}
    x = x / (np.max(np.abs(x)) + _EPS)

    import librosa
    S = np.abs(librosa.stft(x, n_fft=_N_FFT, hop_length=_HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=SR, n_fft=_N_FFT)

    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return S[m].sum(axis=0)

    low = band(20, 200)          # breath / pop / proximity
    speech = band(300, 3400) + _EPS
    high = band(3400, 8000)
    total = S.sum(axis=0) + _EPS

    voiced = total > np.percentile(total, 60)   # focus on speech-active frames
    if voiced.sum() < 4:
        return {"low_ratio": 0.0, "pop_rate": 0.0, "high_ratio": 0.0, "flatness": 0.0, "n": 0}

    low_ratio = float(np.mean(low[voiced] / speech[voiced]))
    high_ratio = float(np.mean(high[voiced] / speech[voiced]))
    # pop transients: low-band frames spiking well above the low-band median
    med = np.median(low[voiced]) + _EPS
    pop_rate = float(np.mean((low[voiced] / med) > 3.0))
    # spectral flatness (geometric/arithmetic mean over freq) — replay is flatter/colored
    flatness = float(np.mean(librosa.feature.spectral_flatness(S=np.sqrt(S[:, voiced]))))

    return {"low_ratio": round(low_ratio, 4), "pop_rate": round(pop_rate, 4),
            "high_ratio": round(high_ratio, 4), "flatness": round(flatness, 4),
            "n": int(voiced.sum())}


def pop_score(wav16k: np.ndarray) -> float:
    """Combined 0-1 liveness score, higher = more consistent with a live near-field
    voice. This default weighting is a starting point; calibrate_popnoise.py picks
    the best single feature + threshold on real data. Non-blocking until then."""
    f = analyze(wav16k)
    if f["n"] == 0:
        return 0.0
    # squashing constants chosen so typical near-field speech lands mid/high and a
    # bass-rolled-off replay lands low; refined by calibration, not load-bearing.
    low = 1.0 - np.exp(-f["low_ratio"] / 0.04)      # proximity/breath present
    pops = min(1.0, f["pop_rate"] / 0.15)           # plosive pops present
    return float(np.clip(0.6 * low + 0.4 * pops, 0.0, 1.0))


if __name__ == "__main__":
    # sanity: silence scores ~0; a low-frequency-rich burst scores higher than a
    # band-limited (speaker-like) tone. Not a validation of live-vs-replay (that
    # needs real captures) — just that the feature moves in the right direction.
    import numpy as _np
    sr = SR
    sil = _np.zeros(sr, _np.float32)
    assert pop_score(sil) == 0.0
    t = _np.arange(sr) / sr
    # "near-field": strong low-freq + broadband transients (pop-like)
    live = (0.5 * _np.sin(2 * _np.pi * 90 * t) + 0.3 * _np.random.default_rng(0).standard_normal(sr)).astype(_np.float32)
    live[sr // 3:sr // 3 + 400] += 1.5           # a low-freq pop burst
    # "speaker replay": band-limited (no low end), smoother
    speakerish = (0.5 * _np.sin(2 * _np.pi * 800 * t)).astype(_np.float32)
    s_live, s_rep = pop_score(live), pop_score(speakerish)
    print(f"pop_score live={s_live:.3f}  speaker-like={s_rep:.3f}")
    assert s_live > s_rep, "low-freq/pop-rich audio should score higher than band-limited"
    print("popnoise self-check ok")
