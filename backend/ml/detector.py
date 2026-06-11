import os
import numpy as np

from ml.audio_utils import load_audio_bytes, preprocess
from ml.aasist_model import load_aasist, infer as _aasist_infer
from ml.handcrafted import score_handcrafted
from ml.breath_detector import score_breath
from ml.phase_coherence import score_phase

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_aasist(_MODEL_PATH)
    return _model


# Layer weights — AASIST is the strongest signal
_WEIGHTS = {
    "aasist":   0.45,
    "mfcc":     0.20,
    "breath":   0.20,
    "phase":    0.15,
    "liveness": 0.00,   # Phase 1D
}


def detect_audio(audio_bytes: bytes) -> dict:
    """
    Run all active layers on raw audio bytes.
    Returns dict with risk_score (0-100), alert_level, and layer_breakdown.
    """
    audio, _ = load_audio_bytes(audio_bytes)
    processed = preprocess(audio)
    model = _get_model()

    scores = {
        "aasist":   _aasist_infer(model, processed),
        "mfcc":     score_handcrafted(processed),
        "breath":   score_breath(audio),
        "phase":    score_phase(processed),
        "liveness": 0.0,
    }

    risk_float = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
    risk_score = int(round(np.clip(risk_float * 100, 0, 100)))

    if risk_score >= 70:
        alert_level = "RED"
    elif risk_score >= 40:
        alert_level = "AMBER"
    else:
        alert_level = "GREEN"

    return {
        "risk_score": risk_score,
        "alert_level": alert_level,
        "layer_breakdown": {k: int(round(v * 100)) for k, v in scores.items()},
    }
