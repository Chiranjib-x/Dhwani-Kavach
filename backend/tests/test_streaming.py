import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from app.routes.websocket import _drain_windows, _WINDOW, _HOP
from ml.audio_utils import SAMPLE_RATE


def test_short_buffer_yields_nothing():
    buf = np.zeros(_WINDOW - 1, dtype=np.float32)
    windows, leftover = _drain_windows(buf)
    assert windows == []
    assert len(leftover) == _WINDOW - 1  # untouched, waiting for more frames
    print("  [OK] sub-window buffer is held, not scored")


def test_exact_window_slides_by_hop():
    buf = np.zeros(_WINDOW, dtype=np.float32)
    windows, leftover = _drain_windows(buf)
    assert len(windows) == 1 and len(windows[0]) == _WINDOW
    assert len(leftover) == _WINDOW - _HOP  # slid forward 5s -> 5s remains
    print("  [OK] one window, buffer slid forward by hop")


def test_overlap_is_50pct():
    # 20s of a ramp so each window is identifiable by its first sample.
    buf = np.arange(SAMPLE_RATE * 20, dtype=np.float32)
    windows, leftover = _drain_windows(buf)
    starts = [int(w[0]) for w in windows]
    # _drain_windows returns EVERY complete window (the handler then scores only
    # the newest); consecutive starts spaced by _HOP, and _HOP == _WINDOW // 2 is
    # the 50% overlap.
    assert starts == list(range(0, len(starts) * _HOP, _HOP)), starts
    assert _HOP == _WINDOW // 2, "50% overlap requires hop == window/2"
    assert len(leftover) < _WINDOW, len(leftover)
    print(f"  [OK] {len(windows)} windows spaced by {_HOP // SAMPLE_RATE}s (50% overlap)")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 2B — streaming window accumulator")
    print("=" * 50)
    failed = []
    for t in (test_short_buffer_yields_nothing, test_exact_window_slides_by_hop, test_overlap_is_50pct):
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
