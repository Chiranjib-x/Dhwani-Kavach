import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import numpy as np
import soundfile as sf

from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES
from ml.handcrafted import score_handcrafted
from ml.breath_detector import score_breath
from ml.phase_coherence import score_phase
from ml.detector import detect_audio


# ── helpers ─────────────────────────────────────────────────────────────────

def make_sine(freq=440.0, dur=4.0, sr=SAMPLE_RATE) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def make_noise(dur=4.0, sr=SAMPLE_RATE) -> np.ndarray:
    rng = np.random.RandomState(7)
    return (rng.randn(int(sr * dur)) * 0.1).astype(np.float32)


def make_speech_like(dur=4.0, sr=SAMPLE_RATE) -> np.ndarray:
    """Synthetic 'speech-like' signal: AM-modulated harmonics with breath-noise pauses."""
    rng = np.random.RandomState(42)
    rng_breath = np.random.RandomState(99)
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    sig = np.zeros_like(t)
    for f0 in [120.0, 200.0, 280.0]:
        harmonics = sum(np.sin(2 * np.pi * k * f0 * t) / k for k in range(1, 8))
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t)
        sig += harmonics * mod
    # Replace pauses with low-energy broadband noise (simulates breathing)
    for start, end in [(0.8, 1.0), (2.2, 2.5), (3.5, 3.7)]:
        i0, i1 = int(start * sr), int(end * sr)
        sig[i0:i1] = rng_breath.randn(i1 - i0).astype(np.float32) * 0.015
    sig = (sig / (np.abs(sig).max() + 1e-8) * 0.5).astype(np.float32)
    return sig


def audio_to_bytes(audio: np.ndarray, sr: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


# ── Layer 2: handcrafted ─────────────────────────────────────────────────────

def test_handcrafted_range_sine():
    score = score_handcrafted(make_sine())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] handcrafted sine score in [0,1]: {score:.3f}")


def test_handcrafted_range_noise():
    score = score_handcrafted(make_noise())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] handcrafted noise score in [0,1]: {score:.3f}")


def test_handcrafted_speech_lower_than_sine():
    # Speech-like audio should score lower (less suspicious) than a pure sine
    speech_score = score_handcrafted(make_speech_like())
    sine_score = score_handcrafted(make_sine())
    assert speech_score < sine_score, (
        f"Speech ({speech_score:.3f}) should score lower than sine ({sine_score:.3f})"
    )
    print(f"  [OK] speech ({speech_score:.3f}) < sine ({sine_score:.3f})")


# ── Layer 3: breath detector ─────────────────────────────────────────────────

def test_breath_range_speech():
    score = score_breath(make_speech_like())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] breath speech score in [0,1]: {score:.3f}")


def test_breath_range_sine():
    score = score_breath(make_sine())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] breath sine score in [0,1]: {score:.3f}")


def test_breath_speech_lower_than_sine():
    # Speech-like signal has pauses; pure sine has none -> sine gets higher score
    speech_score = score_breath(make_speech_like())
    sine_score = score_breath(make_sine())
    assert speech_score < sine_score, (
        f"Speech ({speech_score:.3f}) should score lower than sine ({sine_score:.3f})"
    )
    print(f"  [OK] breath: speech ({speech_score:.3f}) < sine ({sine_score:.3f})")


# ── Layer 4: phase coherence ─────────────────────────────────────────────────

def test_phase_range_speech():
    score = score_phase(make_speech_like())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] phase speech score in [0,1]: {score:.3f}")


def test_phase_range_sine():
    score = score_phase(make_sine())
    assert 0.0 <= score <= 1.0
    print(f"  [OK] phase sine score in [0,1]: {score:.3f}")


def test_phase_sine_suspicious():
    # A pure sine has perfectly regular phase -> very low deviation -> suspicious
    score = score_phase(make_sine())
    assert score > 0.0, "pure sine should have non-zero phase suspicion"
    print(f"  [OK] phase sine is suspicious: {score:.3f}")


# ── End-to-end: detect_audio ─────────────────────────────────────────────────

def test_detect_audio_keys():
    result = detect_audio(audio_to_bytes(make_speech_like()))
    assert "risk_score" in result
    assert "alert_level" in result
    assert "layer_breakdown" in result
    breakdown = result["layer_breakdown"]
    for key in ["aasist", "mfcc", "breath", "phase", "liveness"]:
        assert key in breakdown, f"missing key: {key}"
    print(f"  [OK] detect_audio keys present")


def test_detect_audio_risk_range():
    result = detect_audio(audio_to_bytes(make_speech_like()))
    assert 0 <= result["risk_score"] <= 100
    print(f"  [OK] detect_audio risk_score={result['risk_score']}")


def test_detect_audio_alert_levels():
    result = detect_audio(audio_to_bytes(make_speech_like()))
    assert result["alert_level"] in ("GREEN", "AMBER", "RED")
    print(f"  [OK] detect_audio alert_level={result['alert_level']}")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1C -- Layers 2-4 + Detector Tests")
    print("=" * 50)
    tests = [
        test_handcrafted_range_sine,
        test_handcrafted_range_noise,
        test_handcrafted_speech_lower_than_sine,
        test_breath_range_speech,
        test_breath_range_sine,
        test_breath_speech_lower_than_sine,
        test_phase_range_speech,
        test_phase_range_sine,
        test_phase_sine_suspicious,
        test_detect_audio_keys,
        test_detect_audio_risk_range,
        test_detect_audio_alert_levels,
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
        print(f"All {len(tests)} tests passed. Phase 1C complete.")
