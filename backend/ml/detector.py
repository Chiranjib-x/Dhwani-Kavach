import os
import numpy as np

from ml.audio_utils import load_audio_bytes, chunk_audio
from ml.aasist_model import load_aasist, infer as _aasist_infer
from ml.handcrafted import score_handcrafted
from ml.breath_detector import score_breath
from ml.phase_coherence import score_phase
from ml.liveness import score_liveness
from ml.ensemble import compute_ensemble

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
_model = None

# ponytail: cap chunks so a long call can't blow up latency (~0.5s/chunk on CPU).
# Beyond this we stride across the whole file rather than only its first minute.
_MAX_CHUNKS = 16


def _get_model():
    global _model
    if _model is None:
        _model = load_aasist(_MODEL_PATH)
    return _model


def _score_chunk(model, chunk: np.ndarray) -> dict:
    return {
        "aasist":   _aasist_infer(model, chunk),
        "mfcc":     score_handcrafted(chunk),
        "breath":   score_breath(chunk),
        "phase":    score_phase(chunk),
        "liveness": score_liveness(chunk),
    }


def detect_audio(audio_bytes: bytes) -> dict:
    """
    Run all 5 layers across the whole recording, not just its first 4s.
    Audio is split into ~4s chunks; the highest-risk chunk drives the verdict
    (a deepfake anywhere in the call is a deepfake). Returns dict with
    risk_score (0-100), alert_level, and layer_breakdown of that worst chunk.
    """
    audio, _ = load_audio_bytes(audio_bytes)
    model = _get_model()

    chunks = chunk_audio(audio)
    if len(chunks) > _MAX_CHUNKS:
        chunks = chunks[:: -(-len(chunks) // _MAX_CHUNKS)]  # stride to span whole file

    per_chunk = [_score_chunk(model, c) for c in chunks]
    worst = max(per_chunk, key=lambda s: compute_ensemble(s)["risk_score"])

    result = compute_ensemble(worst)
    result["layer_breakdown"] = {k: int(round(v * 100)) for k, v in worst.items()}
    return result
