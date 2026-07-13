import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from eval.run import _eer, _auc, _metrics


def test_perfect_separation():
    fake = np.array([0.9, 0.95, 0.99]); real = np.array([0.01, 0.05, 0.1])
    eer, _ = _eer(fake, real)
    assert eer < 0.01, f"perfect separation should give ~0 EER, got {eer}"
    assert _auc(fake, real) == 1.0, "perfect separation -> AUC 1.0"
    print(f"  [OK] perfect separation: EER={eer:.1%} AUC=1.000")


def test_no_separation():
    fake = np.array([0.5, 0.5, 0.5]); real = np.array([0.5, 0.5, 0.5])
    eer, _ = _eer(fake, real)
    assert abs(eer - 0.5) < 0.01 or eer <= 0.5, f"overlapping -> ~0.5 EER, got {eer}"
    assert abs(_auc(fake, real) - 0.5) < 1e-9, "identical scores -> AUC 0.5 (all ties)"
    print(f"  [OK] no separation: EER={eer:.1%} AUC=0.500")


def test_metrics_far_frr():
    # spoof scored high, bonafide low; at op-threshold 0.5 both perfectly classified.
    m = _metrics(np.array([0.8, 0.9]), np.array([0.1, 0.2]), t_op=0.5)
    assert m["far"] == 0.0 and m["frr"] == 0.0 and m["acc"] == 1.0, m
    print(f"  [OK] FAR/FRR/acc at threshold: far={m['far']:.0%} frr={m['frr']:.0%} acc={m['acc']:.0%}")


if __name__ == "__main__":
    print("=" * 50)
    print("eval harness -- metric math")
    print("=" * 50)
    failed = []
    for t in (test_perfect_separation, test_no_separation, test_metrics_far_frr):
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print("=" * 50)
    if failed:
        print(f"FAILED: {failed}"); sys.exit(1)
    print("All tests passed.")
