import os
import numpy as np

from ml.audio_utils import load_audio_bytes, preprocess
from ml.aasist_model import load_aasist, infer as _aasist_infer
from ml.handcrafted import score_handcrafted
from ml.breath_detector import score_breath
from ml.phase_coherence import score_phase
from ml.liveness import score_liveness
from ml.ensemble import compute_ensemble

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_aasist(_MODEL_PATH)
    return _model


def detect_audio(audio_bytes: bytes) -> dict:
    """
    Run all 5 layers on raw audio bytes.
    Returns dict with risk_score (0-100), alert_level, and layer_breakdown.
    """
    audio, _ = load_audio_bytes(audio_bytes)
    processed = preprocess(audio)
    model = _get_model()

    layer_scores = {
        "aasist":   _aasist_infer(model, processed),
        "mfcc":     score_handcrafted(processed),
        "breath":   score_breath(audio),
        "phase":    score_phase(processed),
        "liveness": score_liveness(audio),
    }

    result = compute_ensemble(layer_scores)
    result["layer_breakdown"] = {
        k: int(round(v * 100)) for k, v in layer_scores.items()
    }
    return result
