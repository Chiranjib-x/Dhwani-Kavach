import random
import uuid
import numpy as np
import librosa
from ml.audio_utils import SAMPLE_RATE, preprocess


def generate_challenge() -> dict:
    """
    Generate a spoken-digit liveness challenge.

    Note: this produces a prompt only. Verifying that the caller
    actually spoke the correct digits requires speech recognition
    (e.g. Whisper) — not yet integrated. The liveness SCORE below
    is based on acoustic properties of the response audio, not on
    content matching.
    """
    digits = [random.randint(0, 9) for _ in range(4)]
    return {
        "challenge_id": str(uuid.uuid4())[:8],
        "prompt": f"Please say the following digits: {', '.join(map(str, digits))}",
        "digits": digits,
        "note": "Content verification requires ASR — not yet integrated.",
    }


def score_liveness(audio: np.ndarray) -> float:
    """
    Layer 5: acoustic liveness heuristics.

    Checks three properties that distinguish a live microphone recording
    from a synthesised or replayed audio stream:

      1. Pitch jitter  — live voices have natural cycle-to-cycle F0 variation.
      2. Noise floor   — real microphones always have a low-level noise floor;
                         purely synthetic audio is often suspiciously clean.
      3. Syllabic AM   — natural speech has strong amplitude modulation from
                         the breath-syllable rhythm; flat envelopes are suspicious.

    Returns spoof probability in [0, 1].  Higher = more likely NOT a live human.
    """
    audio = preprocess(audio)
    sr = SAMPLE_RATE
    weighted_scores: list[tuple[float, float]] = []

    # ── Pitch jitter ─────────────────────────────────────────────────────────
    try:
        f0 = librosa.yin(audio, fmin=50, fmax=500, sr=sr,
                         frame_length=2048, hop_length=256)
        voiced = f0[(f0 > 60) & (f0 < 450)]
        if len(voiced) >= 20:
            jitter = float(np.std(np.diff(voiced)) / (np.mean(voiced) + 1e-8))
            # jitter >= 0.015 -> score 0 (live), jitter <= 0.003 -> score 1 (fake)
            jitter_score = float(np.clip(1.0 - (jitter - 0.003) / 0.012, 0.0, 1.0))
            weighted_scores.append((jitter_score, 0.40))
    except Exception:
        pass

    # ── Noise floor ──────────────────────────────────────────────────────────
    rms = librosa.feature.rms(y=audio, frame_length=512, hop_length=160)[0]
    n_quiet = max(len(rms) // 10, 5)
    noise_floor = float(np.mean(np.sort(rms)[:n_quiet]))
    # Realistic mic noise floor: 5e-4 to 5e-3. Below 5e-5 = suspiciously clean.
    nf_score = float(np.clip(1.0 - noise_floor / 5e-4, 0.0, 1.0))
    weighted_scores.append((nf_score, 0.30))

    # ── Syllabic AM depth ────────────────────────────────────────────────────
    envelope = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
    am_depth = float(np.std(envelope) / (np.mean(envelope) + 1e-8))
    # am_depth >= 0.40 -> score 0 (natural), am_depth <= 0.10 -> score 1
    am_score = float(np.clip(1.0 - (am_depth - 0.10) / 0.30, 0.0, 1.0))
    weighted_scores.append((am_score, 0.30))

    total_w = sum(w for _, w in weighted_scores)
    return float(np.clip(sum(s * w for s, w in weighted_scores) / total_w, 0.0, 1.0))
