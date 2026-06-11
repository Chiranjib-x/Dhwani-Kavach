import numpy as np
import librosa
from ml.audio_utils import SAMPLE_RATE


_FRAME_LEN = int(0.025 * SAMPLE_RATE)   # 25 ms
_HOP_LEN   = int(0.010 * SAMPLE_RATE)   # 10 ms
_MIN_BREATH_FRAMES = 5                   # ~50 ms minimum breath duration
_MAX_BREATH_FRAMES = 30                  # ~300 ms maximum


def _find_breath_events(audio: np.ndarray) -> int:
    """Count breath-like events: brief segments of low energy with broadband content."""
    rms = librosa.feature.rms(y=audio, frame_length=_FRAME_LEN,
                               hop_length=_HOP_LEN)[0]
    flatness = librosa.feature.spectral_flatness(y=audio, n_fft=512,
                                                  hop_length=_HOP_LEN)[0]
    n = min(len(rms), len(flatness))
    rms, flatness = rms[:n], flatness[:n]

    rms_norm = rms / (rms.max() + 1e-8)

    # Candidate: low energy AND some broadband noise content (flatness > 0.05)
    # Threshold lowered vs original to catch low-amplitude noise in real breath pauses
    is_candidate = (rms_norm > 0.005) & (rms_norm < 0.12) & (flatness > 0.05)

    events = 0
    run = 0
    for flag in is_candidate:
        if flag:
            run += 1
        else:
            if _MIN_BREATH_FRAMES <= run <= _MAX_BREATH_FRAMES:
                events += 1
            run = 0
    if _MIN_BREATH_FRAMES <= run <= _MAX_BREATH_FRAMES:
        events += 1
    return events


def score_breath(audio: np.ndarray) -> float:
    """
    Layer 3: breath/pause pattern analysis.
    Real speakers take breaths between phrases (~1-4 per 4 s chunk).
    TTS rarely models breathing. Returns spoof probability in [0, 1].
    """
    events = _find_breath_events(audio)

    if events == 0:
        return 0.75
    elif events == 1:
        return 0.25
    elif events <= 4:
        return 0.10
    else:
        # Excessive events also unusual
        return float(np.clip(0.10 + (events - 4) * 0.10, 0.10, 0.60))
