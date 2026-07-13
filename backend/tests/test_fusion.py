import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml import fusion


def test_voice_red_tracks_calibration_threshold():
    # Threshold-consistency fix: fuse()'s voice_red must use the SAME t_high
    # as ml.detector's alert_level banding, not an independent hardcoded 70 --
    # otherwise a RED badge can pair with a MONITOR action.
    fusion._score_thresholds = lambda: (25, 50)

    below = fusion.fuse(deepfake_risk=45)
    assert below["action"] == "MONITOR", below                  # 45 < 50 -> no threat

    at_threshold = fusion.fuse(deepfake_risk=50)
    assert at_threshold["action"] == "CHALLENGE", at_threshold  # 50 >= 50 -> threat
    print("  [OK] voice_red follows the injected threshold, not a hardcoded 70")


def test_novelty_never_causes_action_alone():
    fusion._score_thresholds = lambda: (25, 50)
    result = fusion.fuse(deepfake_risk=10, scam_score=0, novelty=0.9)
    assert result["action"] == "MONITOR", result
    assert "elevated novelty noted" in result["action_reason"], result
    print("  [OK] high novelty alone stays MONITOR, noted but not causal")


def test_block_on_high_value_threat():
    fusion._score_thresholds = lambda: (25, 50)
    result = fusion.fuse(deepfake_risk=80, txn={"amount": 100_000})
    assert result["action"] == "BLOCK", result
    print("  [OK] threat + high-value txn -> BLOCK")


if __name__ == "__main__":
    print("=" * 50)
    print("fusion -- decision fusion")
    print("=" * 50)
    failed = []
    for t in (test_voice_red_tracks_calibration_threshold,
              test_novelty_never_causes_action_alone,
              test_block_on_high_value_threat):
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
