import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import ml.detector as detector
from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES


def _fake_setup(monkeyscores):
    """Patch the model + per-chunk scorer so detect_audio runs without torch.
    monkeyscores: callable(chunk) -> layer-score dict."""
    detector._get_model = lambda: object()
    detector._score_chunk = lambda model, chunk: monkeyscores(chunk)


def test_worst_chunk_drives_verdict():
    # First chunk looks clean, a later chunk looks fake. Verdict must follow the fake one.
    calls = {"i": 0}
    def scorer(chunk):
        calls["i"] += 1
        fake = calls["i"] == 3  # third chunk is the spoof
        v = 0.9 if fake else 0.0
        return {k: v for k in ("aasist", "mfcc", "breath", "phase", "liveness")}
    _fake_setup(scorer)

    audio = np.zeros(CHUNK_SAMPLES * 5, dtype=np.float32)
    detector.load_audio_bytes = lambda b: (audio, SAMPLE_RATE)
    out = detector.detect_audio(b"x")
    assert out["risk_score"] == 90, out          # worst chunk (0.9) wins, not the mean
    assert out["alert_level"] == "RED", out
    print("  [OK] worst chunk drives verdict")


def test_chunk_count_capped_and_spans_file():
    seen = []
    def scorer(chunk):
        seen.append(chunk[0])  # record a fingerprint of which chunk was scored
        return {k: 0.0 for k in ("aasist", "mfcc", "breath", "phase", "liveness")}
    _fake_setup(scorer)

    # long file -> far more than _MAX_CHUNKS raw chunks
    n = CHUNK_SAMPLES * 80
    audio = np.arange(n, dtype=np.float32)  # strictly increasing so chunks differ
    detector.load_audio_bytes = lambda b: (audio, SAMPLE_RATE)
    detector.detect_audio(b"x")

    assert len(seen) <= detector._MAX_CHUNKS, f"not capped: {len(seen)}"
    assert seen[0] == 0.0, "striding dropped the start of the file"
    assert seen[-1] > audio[len(audio) // 2], "striding never reached the file's tail"
    print(f"  [OK] capped at {len(seen)} chunks, spans whole file")


if __name__ == "__main__":
    print("=" * 50)
    print("Detector — chunked whole-file analysis")
    print("=" * 50)
    failed = []
    for t in (test_worst_chunk_drives_verdict, test_chunk_count_capped_and_spans_file):
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
