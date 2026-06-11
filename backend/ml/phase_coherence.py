import numpy as np
import librosa
from ml.audio_utils import SAMPLE_RATE, preprocess

_N_FFT = 512
_HOP   = 160


def score_phase(audio: np.ndarray) -> float:
    """
    Layer 4: temporal variance of STFT phase deviation.
    Vocoders and pure tones have unnaturally consistent phase across frames
    (low variance); natural speech has significant frame-to-frame variation.
    Returns spoof probability in [0, 1].
    """
    audio = preprocess(audio)
    D = librosa.stft(audio, n_fft=_N_FFT, hop_length=_HOP)   # (F, T)

    mag   = np.abs(D)
    phase = np.angle(D)

    # Ideal phase advance per hop for each frequency bin
    expected_dphi = (2.0 * np.pi * np.arange(D.shape[0]) * _HOP / _N_FFT)[:, None]

    # Deviation of measured phase advance from ideal (principal value)
    dphi = np.diff(phase, axis=1)                              # (F, T-1)
    dev  = dphi - expected_dphi
    dev  = dev - 2.0 * np.pi * np.round(dev / (2.0 * np.pi)) # wrap to [-pi, pi]

    # Temporal variance of deviation per frequency bin
    dev_var  = np.var(dev, axis=1)                            # (F,)
    mag_avg  = mag[:, :-1].mean(axis=1) + 1e-8
    weighted_var = float(np.sum(dev_var * mag_avg) / np.sum(mag_avg))

    # Low variance → regular/synthetic; threshold ~0.5 rad^2 separates real from fake
    score = float(np.clip(1.0 - weighted_var / 0.5, 0.0, 1.0))
    return score
