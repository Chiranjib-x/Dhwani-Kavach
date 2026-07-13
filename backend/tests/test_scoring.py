import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.scoring import StreamAggregator


def test_single_spike_does_not_confirm_red():
    agg = StreamAggregator(t_low=0.45, t_high=0.72, confirm=2)
    levels = [agg.update(p)["alert_level"] for p in [0.05, 0.05, 0.95, 0.05, 0.05]]
    assert "RED" not in levels, f"single spike must not confirm RED: {levels}"
    print("  [OK] single spike suppressed (confirmation + EWMA damping)")


def test_sustained_high_risk_confirms_red():
    agg = StreamAggregator(t_low=0.45, t_high=0.72, confirm=2)
    levels = [agg.update(0.95)["alert_level"] for _ in range(5)]
    assert "RED" in levels, f"sustained high risk must confirm RED: {levels}"
    print("  [OK] sustained high risk confirms RED")


def test_hysteresis_clears_after_sustained_low_risk():
    agg = StreamAggregator(t_low=0.45, t_high=0.72, confirm=2)
    for _ in range(5):
        agg.update(0.95)
    mid = agg.update(0.55)  # between t_low and t_high
    assert mid["alert_level"] == "RED", "hysteresis must hold RED above t_low"
    for _ in range(12):
        low = agg.update(0.02)
    assert low["alert_level"] == "GREEN", "must clear after sustained low risk"
    print("  [OK] hysteresis holds RED above t_low, then clears on sustained low risk")


if __name__ == "__main__":
    print("=" * 50)
    print("StreamAggregator — EWMA + confirmation + hysteresis")
    print("=" * 50)
    failed = []
    for t in (test_single_spike_does_not_confirm_red,
              test_sustained_high_risk_confirms_red,
              test_hysteresis_clears_after_sustained_low_risk):
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
