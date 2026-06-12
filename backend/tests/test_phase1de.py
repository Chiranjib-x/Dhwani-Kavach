import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import numpy as np
import soundfile as sf

from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES
from ml.liveness import generate_challenge, score_liveness
from ml.ensemble import compute_ensemble, WEIGHTS
from ml.detector import detect_audio


# ── helpers ─────────────────────────────────────────────────────────────────

def make_sine(freq=440.0, dur=4.0) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def make_speech_like(dur=4.0) -> np.ndarray:
    rng = np.random.RandomState(42)
    rng_b = np.random.RandomState(99)
    sr = SAMPLE_RATE
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    sig = np.zeros_like(t)
    for f0 in [120.0, 200.0, 280.0]:
        harmonics = sum(np.sin(2 * np.pi * k * f0 * t) / k for k in range(1, 8))
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t)
        sig += harmonics * mod
    for start, end in [(0.8, 1.0), (2.2, 2.5), (3.5, 3.7)]:
        i0, i1 = int(start * sr), int(end * sr)
        sig[i0:i1] = rng_b.randn(i1 - i0).astype(np.float32) * 0.015
    sig += rng.randn(len(sig)).astype(np.float32) * 2e-4   # mic noise floor
    return (sig / (np.abs(sig).max() + 1e-8) * 0.5).astype(np.float32)


def audio_to_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    return buf.getvalue()


# ── Phase 1D: liveness ───────────────────────────────────────────────────────

def test_generate_challenge_keys():
    ch = generate_challenge()
    assert "challenge_id" in ch
    assert "prompt" in ch
    assert "digits" in ch
    assert len(ch["digits"]) == 4
    assert all(0 <= d <= 9 for d in ch["digits"])
    print(f"  [OK] generate_challenge: {ch['prompt']}")


def test_generate_challenge_unique():
    ids = {generate_challenge()["challenge_id"] for _ in range(20)}
    assert len(ids) == 20, "challenge IDs should be unique"
    print("  [OK] challenge IDs are unique")


def test_liveness_range_sine():
    score = score_liveness(make_sine())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] liveness sine in [0,1]: {score:.3f}")


def test_liveness_range_speech():
    score = score_liveness(make_speech_like())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] liveness speech in [0,1]: {score:.3f}")


def test_liveness_sine_more_suspicious():
    # Pure sine has no pitch jitter, no noise floor -> more suspicious than speech
    sine_score = score_liveness(make_sine())
    speech_score = score_liveness(make_speech_like())
    assert sine_score > speech_score, (
        f"Sine ({sine_score:.3f}) should be more suspicious than speech ({speech_score:.3f})"
    )
    print(f"  [OK] liveness: sine ({sine_score:.3f}) > speech ({speech_score:.3f})")


# ── Phase 1E: ensemble ───────────────────────────────────────────────────────

def test_ensemble_weights_sum():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"
    print(f"  [OK] ensemble weights sum to 1.0")


def test_ensemble_all_zero():
    result = compute_ensemble({k: 0.0 for k in WEIGHTS})
    assert result["risk_score"] == 0
    assert result["alert_level"] == "GREEN"
    print("  [OK] all-zero scores -> GREEN risk_score=0")


def test_ensemble_all_one():
    result = compute_ensemble({k: 1.0 for k in WEIGHTS})
    assert result["risk_score"] == 100
    assert result["alert_level"] == "RED"
    print("  [OK] all-one scores -> RED risk_score=100")


def test_ensemble_thresholds():
    # GREEN < 40, AMBER 40-69, RED >= 70
    for score_val, expected_level in [(0.30, "GREEN"), (0.55, "AMBER"), (0.80, "RED")]:
        result = compute_ensemble({k: score_val for k in WEIGHTS})
        assert result["alert_level"] == expected_level, (
            f"score={score_val} expected {expected_level} got {result['alert_level']}"
        )
    print("  [OK] ensemble alert thresholds GREEN/AMBER/RED correct")


def test_ensemble_risk_range():
    import random
    random.seed(0)
    for _ in range(20):
        scores = {k: random.random() for k in WEIGHTS}
        result = compute_ensemble(scores)
        assert 0 <= result["risk_score"] <= 100
    print("  [OK] ensemble risk_score always in [0, 100]")


# ── Full pipeline ────────────────────────────────────────────────────────────

def test_detect_audio_all_layers():
    result = detect_audio(audio_to_bytes(make_speech_like()))
    breakdown = result["layer_breakdown"]
    for key in ("aasist", "mfcc", "breath", "phase", "liveness"):
        assert key in breakdown, f"missing layer: {key}"
        assert 0 <= breakdown[key] <= 100, f"{key} out of range: {breakdown[key]}"
    print(f"  [OK] all 5 layers present: {breakdown}")


def test_detect_audio_liveness_active():
    result = detect_audio(audio_to_bytes(make_speech_like()))
    assert result["layer_breakdown"]["liveness"] >= 0
    print(f"  [OK] liveness layer active: {result['layer_breakdown']['liveness']}")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1D+1E -- Liveness + Ensemble Tests")
    print("=" * 50)
    tests = [
        test_generate_challenge_keys,
        test_generate_challenge_unique,
        test_liveness_range_sine,
        test_liveness_range_speech,
        test_liveness_sine_more_suspicious,
        test_ensemble_weights_sum,
        test_ensemble_all_zero,
        test_ensemble_all_one,
        test_ensemble_thresholds,
        test_ensemble_risk_range,
        test_detect_audio_all_layers,
        test_detect_audio_liveness_active,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print("=" * 50)
    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed. Phase 1D+1E complete.")
