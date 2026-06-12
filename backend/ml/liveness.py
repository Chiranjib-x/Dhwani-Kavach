import random
import uuid
import numpy as np
import librosa
from ml.audio_utils import SAMPLE_RATE, preprocess


def generate_challenge() -> dict:
    """Return a spoken-digit challenge for the caller."""
    digits = [random.randint(0, 9) for _ in range(4)]
    return {
        "challenge_id": str(uuid.uuid4())[:8],
        "prompt": f"Please say the following digits: {', '.join(map(str, digits))}",
        "digits": digits,
    }


def score_liveness(audio: np.ndarray) -> float:
    """
    Layer 5: liveness detection heuristics.
    Checks pitch jitter, noise floor, and syllabic AM depth.
    Returns spoof probability in [0, 1]; higher = more likely not live.
    """
    audio = preprocess(audio)
    sr = SAMPLE_RATE

    weighted_scores: list[tuple[float, float]] = []  # (score, weight)

    # ── Pitch jitter ─────────────────────────────────────────────────────────
    # Live voice has natural cycle-to-cycle F0 variation (~1-3%).
    # Synthesised / replayed audio often has lower jitter.
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
    # Real microphone recordings have a consistent low-level noise floor.
    # Purely synthesised audio often lacks this; replayed audio varies.
    rms = librosa.feature.rms(y=audio, frame_length=512, hop_length=160)[0]
    n_quiet = max(len(rms) // 10, 5)
    noise_floor = float(np.mean(np.sort(rms)[:n_quiet]))
    # Floor in [5e-4, 5e-3] is realistic for a live mic recording.
    # Below 5e-5 -> suspiciously clean.
    nf_score = float(np.clip(1.0 - noise_floor / 5e-4, 0.0, 1.0))
    weighted_scores.append((nf_score, 0.30))

    # ── Syllabic AM depth ────────────────────────────────────────────────────
    # Natural speech has strong amplitude modulation from syllable rhythm.
    # Too-flat envelope (low std/mean) = synthesiser or replay artefact.
    envelope = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
    am_depth = float(np.std(envelope) / (np.mean(envelope) + 1e-8))
    # am_depth >= 0.40 -> score 0 (natural), am_depth <= 0.10 -> score 1
    am_score = float(np.clip(1.0 - (am_depth - 0.10) / 0.30, 0.0, 1.0))
    weighted_scores.append((am_score, 0.30))

    total_w = sum(w for _, w in weighted_scores)
    return float(np.clip(sum(s * w for s, w in weighted_scores) / total_w, 0.0, 1.0))
