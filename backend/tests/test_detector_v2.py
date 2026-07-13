import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from ml.audio_utils import SAMPLE_RATE
from ml import detector_v2


def make_speech_like(dur=2.0, sr=SAMPLE_RATE) -> np.ndarray:
    """Short synthetic speech-like clip -- same generator style test_phase1c.py
    and test_phase1de.py use (AM-modulated harmonics + a breath-noise pause)."""
    rng_breath = np.random.RandomState(99)
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    sig = np.zeros_like(t)
    for f0 in [120.0, 200.0, 280.0]:
        harmonics = sum(np.sin(2 * np.pi * k * f0 * t) / k for k in range(1, 8))
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t)
        sig += harmonics * mod
    i0, i1 = int(0.4 * sr), int(0.6 * sr)
    sig[i0:i1] = rng_breath.randn(i1 - i0).astype(np.float32) * 0.015
    sig = (sig / (np.abs(sig).max() + 1e-8) * 0.5).astype(np.float32)
    return sig


def test_infer_returns_float_in_range():
    if not detector_v2.available():
        print("  [SKIP] no w2v2aasist_cotrain.pt bundled -- detector_v2 not available")
        return
    audio = make_speech_like()
    score = detector_v2.infer(audio)
    assert isinstance(score, float), f"expected float, got {type(score)}"
    assert 0.0 <= score <= 1.0, f"score out of range: {score}"
    print(f"  [OK] detector_v2.infer -> {score:.4f}")


def test_infer_batch_matches_per_item():
    # Batching must be a pure speedup, never a different answer -- the upload path
    # relies on infer_batch producing exactly what per-chunk infer() would.
    if not detector_v2.available():
        print("  [SKIP] detector_v2 not available")
        return
    clips = [make_speech_like(2.0), make_speech_like(3.0) * 0.7, make_speech_like(1.5)]
    per = [detector_v2.infer(c) for c in clips]
    bat = detector_v2.infer_batch(clips)
    assert len(bat) == len(clips), "infer_batch length mismatch"
    d = max(abs(a - b) for a, b in zip(per, bat))
    assert d <= 1e-4, f"infer_batch diverges from per-item infer: max|delta|={d:.2e}"
    assert detector_v2.infer_batch([]) == [], "empty batch must return []"
    print(f"  [OK] infer_batch == per-item (max|delta|={d:.1e})")


if __name__ == "__main__":
    print("=" * 50)
    print("detector_v2 -- W2VAASIST cotrain inference")
    print("=" * 50)
    failed = []
    for t in (test_infer_returns_float_in_range, test_infer_batch_matches_per_item):
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print("=" * 50)
    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    print("All tests passed.")
