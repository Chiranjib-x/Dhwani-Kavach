import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import ml.detector as detector
from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES


def _fake_setup(monkeyscores):
    """Patch the scorer + neural batch + VAD so detect_audio runs without torch.
    monkeyscores: callable(chunk) -> layer-score dict. Also pins calibration to
    identity/40-70 so these tests stay isolated from whatever calibration.json
    happens to be bundled (it's fit against real audio, not these synthetic
    fixtures, and gets refit independently of this suite)."""
    import ml.ensemble as ensemble
    ensemble._FUSION = None                                       # pin hand weights (test asserts their arithmetic)
    detector.vad.available = lambda: False                       # no VAD gating in unit tests
    detector.detector_v2.available = lambda: True                # take the batched neural path
    detector.detector_v2.infer_batch = lambda chunks: [0.0] * len(chunks)  # no real torch
    detector._score_chunk = lambda chunk, neural_score: monkeyscores(chunk)
    detector.calibrate = lambda p: p
    detector._score_thresholds = lambda: (40, 70)


def test_worst_chunk_drives_verdict():
    # First chunk looks clean, a later chunk looks fake. Verdict must follow the fake one.
    calls = {"i": 0}
    def scorer(chunk):
        calls["i"] += 1
        fake = calls["i"] == 3  # third chunk is the spoof
        v = 0.9 if fake else 0.0
        return {k: v for k in ("aasist", "mfcc", "breath", "phase", "liveness")}
    _fake_setup(scorer)

    audio = np.full(CHUNK_SAMPLES * 5, 0.1, dtype=np.float32)  # non-silent so it isn't gated
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


def test_silence_is_gated_to_green():
    # Even if every layer screams "fake", silent audio must never produce a verdict.
    _fake_setup(lambda chunk: {k: 0.9 for k in ("aasist", "mfcc", "breath", "phase", "liveness")})
    silent = np.full(CHUNK_SAMPLES * 3, 1e-5, dtype=np.float32)
    detector.load_audio_bytes = lambda b: (silent, SAMPLE_RATE)
    out = detector.detect_audio(b"x")
    assert out["alert_level"] == "GREEN" and out["risk_score"] == 0, out
    print("  [OK] silence gated to GREEN despite fake-scoring layers")


if __name__ == "__main__":
    print("=" * 50)
    print("Detector — chunked whole-file analysis")
    print("=" * 50)
    failed = []
    for t in (test_worst_chunk_drives_verdict, test_chunk_count_capped_and_spans_file,
              test_silence_is_gated_to_green):
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
