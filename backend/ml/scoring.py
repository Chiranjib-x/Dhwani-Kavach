"""Dhwani-Kavach V2 — calibration + streaming aggregation.

Drop into backend/ml/scoring.py. Replaces:
  - the raw 40/70 banding in ensemble.py
  - the peak-hold-with-decay block in app/routes/websocket.py

Usage (websocket loop):
    from ml.scoring import calibrate, StreamAggregator
    agg = StreamAggregator()                 # one per connection
    ...
    p = detector_v2.infer(window)            # raw softmax spoof prob
    state = agg.update(calibrate(p))         # {"risk_score","alert_level","call_max"}

Usage (upload path, per-chunk scores p1..pN):
    agg = StreamAggregator()
    for p in chunk_probs:
        state = agg.update(calibrate(p))
    call_level = state["call_max"]           # max over the EWMA track

Thresholds come from backend/models/calibration.json written by
tools/fit_calibration.py (Platt scaling on the demo-channel dev kit).
Sensible defaults apply if the file is absent, but DO fit calibration —
that file is worth more than any single model tweak.
"""
from __future__ import annotations

import json
import math
import os

_CAL_PATH = os.environ.get(
    "DHWANI_CALIBRATION",
    os.path.join(os.path.dirname(__file__), "..", "models", "calibration.json"),
)
_DEFAULT = {"a": 1.0, "b": 0.0, "t_low": 0.45, "t_high": 0.72}


def _load_cal() -> dict:
    try:
        with open(_CAL_PATH) as f:
            cal = {**_DEFAULT, **json.load(f)}
    except Exception:
        return dict(_DEFAULT)
    # Safety bounds: a hand-fit or badly-fit calibration must never produce a
    # runaway decision boundary. We shipped a=4.0 once (pivoted from 2
    # anecdotal score buckets) and it flagged live mic audio near-universally.
    # Clamp the slope and force a minimum RED/AMBER margin so a bad
    # calibration.json degrades gracefully instead of breaking every verdict.
    cal["a"] = min(max(float(cal["a"]), 0.5), 1.5)
    # b is the log-odds SHIFT. A fine-tuned model can compress its raw scores
    # toward 0 (whole distribution near-zero), needing a large positive shift to
    # re-center the real/fake boundary -- fit b~5.8 for w2v2aasist_full. The slope
    # clamp above (a) still guards against the runaway that once flagged live mic
    # audio universally; a shift only moves the boundary, it can't over-sharpen.
    cal["b"] = min(max(float(cal["b"]), -8.0), 8.0)
    cal["t_low"] = min(max(float(cal["t_low"]), 0.05), 0.95)
    cal["t_high"] = min(max(float(cal["t_high"]), cal["t_low"] + 0.15), 0.95)
    return cal


_CAL = _load_cal()


def reload_calibration() -> dict:
    """Re-read calibration.json (e.g. after refitting) without a restart."""
    global _CAL
    _CAL = _load_cal()
    return dict(_CAL)


def thresholds() -> tuple[int, int]:
    """Live (t_low, t_high) as 0-100 ints, for callers that band a single
    calibrated score directly (ml.detector, ml.fusion) instead of running
    the EWMA aggregator. Single source of truth so a RED alert_level and a
    CHALLENGE/BLOCK action never disagree about where the line is."""
    return (int(round(_CAL["t_low"] * 100)), int(round(_CAL["t_high"] * 100)))


def calibrate(p_raw: float) -> float:
    """Platt-scaled probability from the model's raw softmax spoof prob."""
    p = min(max(float(p_raw), 1e-6), 1.0 - 1e-6)
    z = math.log(p / (1.0 - p))
    return 1.0 / (1.0 + math.exp(-(_CAL["a"] * z + _CAL["b"])))


class StreamAggregator:
    """EWMA smoothing + two-window confirmation + hysteresis.

    Why: a single 4 s window is a noisy classifier. Raw max-over-windows makes
    call-level false alarms near-certain on long calls (multiple comparisons);
    peak-hold just freezes the mistake. EWMA + confirmation suppresses one-off
    spikes; hysteresis (t_high to enter RED, t_low to leave) stops flicker.
    'One cloned segment flags the call' is preserved via call_max over the
    smoothed track.

    With a 2 s hop and confirm=2, the earliest RED lands ~6 s into speech —
    inside the 10 s first-verdict requirement with margin.
    """

    def __init__(
        self,
        alpha: float = 0.35,
        t_low: float | None = None,
        t_high: float | None = None,
        confirm: int = 2,
    ):
        self.alpha = float(alpha)
        self.confirm = int(confirm)
        self.t_low = _CAL["t_low"] if t_low is None else float(t_low)
        self.t_high = _CAL["t_high"] if t_high is None else float(t_high)
        self.s = 0.0
        self.call_max = 0.0
        self._above = 0
        self._red = False

    def update(self, p_calibrated: float) -> dict:
        p = min(max(float(p_calibrated), 0.0), 1.0)
        self.s = self.alpha * p + (1.0 - self.alpha) * self.s
        self.call_max = max(self.call_max, self.s)

        if self.s >= self.t_high:
            self._above += 1
            if self._above >= self.confirm:
                self._red = True
        else:
            self._above = 0
            if self._red and self.s < self.t_low:
                self._red = False

        level = "RED" if self._red else ("AMBER" if self.s >= self.t_low else "GREEN")
        return {
            "risk_score": int(round(self.s * 100)),
            "alert_level": level,
            "call_max": int(round(self.call_max * 100)),
        }

    def reset(self) -> None:
        self.s = 0.0
        self.call_max = 0.0
        self._above = 0
        self._red = False


if __name__ == "__main__":
    # Self-check: spike suppression, confirmation, hysteresis.
    agg = StreamAggregator(t_low=0.45, t_high=0.72, confirm=2)

    # One-off spike must NOT go RED (confirmation) and EWMA damps it.
    for p in [0.05, 0.05, 0.95, 0.05, 0.05]:
        st = agg.update(p)
    assert st["alert_level"] != "RED", "single spike must not confirm RED"

    # Sustained fake goes RED within a few windows...
    agg.reset()
    levels = [agg.update(0.95)["alert_level"] for _ in range(5)]
    assert "RED" in levels, "sustained high risk must confirm RED"

    # ...and stays RED until the score drops below t_low (hysteresis).
    mid = agg.update(0.55)  # between t_low and t_high
    assert mid["alert_level"] == "RED", "hysteresis must hold RED above t_low"
    for _ in range(12):
        low = agg.update(0.02)
    assert low["alert_level"] == "GREEN", "must clear after sustained low risk"

    print("scoring self-check ok")
