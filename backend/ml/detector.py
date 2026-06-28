import os
import numpy as np

from ml.audio_utils import load_audio_bytes, chunk_audio
from ml.aasist_model import load_aasist, infer as _aasist_infer
from ml import spectrogram_cnn
from ml import wav2vec2_detector
from ml.handcrafted import score_handcrafted
from ml.breath_detector import score_breath
from ml.phase_coherence import score_phase
from ml.liveness import score_liveness
from ml.ensemble import compute_ensemble, WEIGHTS

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
_model = None

# ponytail: cap chunks so a long call can't blow up latency (~0.5s/chunk on CPU).
# Beyond this we stride across the whole file rather than only its first minute.
_MAX_CHUNKS = 16

# ponytail: RMS below this is effectively silence; scoring it just feeds the
# heuristics noise and yields false alarms. Raise if genuinely quiet calls drop.
_SILENCE_RMS = 1e-3


def _get_model():
    # Only needed as a fallback when the trained CNN weights aren't present.
    global _model
    if _model is None:
        _model = load_aasist(_MODEL_PATH)
    return _model


def _neural_infer(model, chunk: np.ndarray) -> float:
    """Best available trained model: wav2vec2 (SSL) > spectrogram CNN > AASIST."""
    if wav2vec2_detector.available():
        return wav2vec2_detector.infer(chunk)
    if spectrogram_cnn.available():
        return spectrogram_cnn.infer(chunk)
    return _aasist_infer(model, chunk)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0


def _score_chunk(model, chunk: np.ndarray) -> dict:
    raw = {
        "aasist":   _neural_infer(model, chunk),
        "mfcc":     score_handcrafted(chunk),
        "breath":   score_breath(chunk),
        "phase":    score_phase(chunk),
        "liveness": score_liveness(chunk),
    }
    # Never let a NaN/out-of-range value from a degenerate chunk reach the ensemble.
    return {k: float(np.clip(np.nan_to_num(v), 0.0, 1.0)) for k, v in raw.items()}


def detect_samples(audio: np.ndarray) -> dict:
    """
    Run all 5 layers across a decoded waveform, not just its first 4s.
    Audio is split into ~4s chunks; the highest-risk chunk drives the verdict
    (a deepfake anywhere in the call is a deepfake). Returns dict with
    risk_score (0-100), alert_level, and layer_breakdown of that worst chunk.
    """
    have_trained = wav2vec2_detector.available() or spectrogram_cnn.available()
    model = None if have_trained else _get_model()

    chunks = chunk_audio(audio)
    if len(chunks) > _MAX_CHUNKS:
        chunks = chunks[:: -(-len(chunks) // _MAX_CHUNKS)]  # stride to span whole file

    # Score only chunks with real audio energy; silence has no honest verdict.
    voiced = [c for c in chunks if _rms(c) >= _SILENCE_RMS]
    if not voiced:
        return {"risk_score": 0, "alert_level": "GREEN",
                "layer_breakdown": {k: 0 for k in WEIGHTS}}

    per_chunk = [_score_chunk(model, c) for c in voiced]
    worst = max(per_chunk, key=lambda s: compute_ensemble(s)["risk_score"])

    result = compute_ensemble(worst)
    result["layer_breakdown"] = {k: int(round(v * 100)) for k, v in worst.items()}
    return result


def detect_audio(audio_bytes: bytes) -> dict:
    """Decode encoded audio bytes (wav/mp3/…) then score the whole recording."""
    audio, _ = load_audio_bytes(audio_bytes)
    return detect_samples(audio)
