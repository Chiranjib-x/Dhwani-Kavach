"""Calibrate the pop-noise / near-field liveness detector on REAL captures — the
step that turns it from researched to enforced.

How to collect the data (5-10 min):
  1. Run the backend with KEEP_AUDIO=1. Clips land in backend/verify_app/captured/.
  2. Record ~8 GENUINE verifies (you, live, phone close to your mouth) and
     ~8 CLONE attempts (your MiniMax/ElevenLabs clone played through a speaker).
  3. Sort them: put genuine clips under captured/live/ and clones under
     captured/clone/ (or just include 'live'/'clone' in each filename).

Then:
  ../.venv/Scripts/python.exe scripts/calibrate_popnoise.py

It reports which feature separates live from replay best, the threshold, the
FAR/FRR at that threshold, and the KV_POP_MIN / KV_POP=1 to switch it on.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

import librosa  # noqa: E402

from verify_app import popnoise  # noqa: E402

_CAPTURED = os.path.join(os.path.dirname(__file__), "..", "verify_app", "captured")
_CLONE_WORDS = ("clone", "replay", "spoof", "fake", "attack")


def _is_clone(path: str) -> bool:
    p = path.lower()
    return any(w in p for w in _CLONE_WORDS)


def _load(path: str) -> np.ndarray:
    y, _ = librosa.load(path, sr=popnoise.SR, mono=True)
    return y.astype(np.float32)


def _best_threshold(live: list[float], clone: list[float]) -> tuple[float, float, float]:
    """Threshold on a 'higher=live' feature that minimizes (FAR+FRR)/2.
    Returns (threshold, FAR=clone accepted, FRR=live rejected)."""
    cand = sorted(set(live + clone))
    best = (0.0, 1.0, 1.0, 2.0)
    for t in cand:
        frr = np.mean([v < t for v in live])          # live wrongly below
        far = np.mean([v >= t for v in clone])         # clone wrongly at/above
        if far + frr < best[3]:
            best = (t, far, frr, far + frr)
    return best[0], best[1], best[2]


def main() -> None:
    files = glob.glob(os.path.join(_CAPTURED, "**", "*.wav"), recursive=True)
    live = [f for f in files if not _is_clone(f)]
    clone = [f for f in files if _is_clone(f)]
    print(f"captured/: {len(live)} live, {len(clone)} clone/replay")
    if len(live) < 3 or len(clone) < 3:
        print("Not enough data. Record ~8 genuine + ~8 clone clips (see this file's docstring).")
        return

    feats = ["low_ratio", "pop_rate", "high_ratio", "pop_score"]
    L = {k: [] for k in feats}
    C = {k: [] for k in feats}
    for grp, paths in (("live", live), ("clone", clone)):
        for p in paths:
            wav = _load(p)
            a = popnoise.analyze(wav)
            a["pop_score"] = popnoise.pop_score(wav)
            for k in feats:
                (L if grp == "live" else C)[k].append(float(a[k]))

    print(f"\n{'feature':12} {'live median':>12} {'clone median':>12} {'thresh':>8} {'FAR':>6} {'FRR':>6}")
    best_overall = None
    for k in feats:
        lm, cm = float(np.median(L[k])), float(np.median(C[k]))
        t, far, frr = _best_threshold(L[k], C[k])
        print(f"{k:12} {lm:12.4f} {cm:12.4f} {t:8.3f} {far:6.2f} {frr:6.2f}")
        if best_overall is None or (far + frr) < best_overall[3]:
            best_overall = (k, t, far, far + frr, frr)

    k, t, far, _, frr = best_overall
    print(f"\nBEST separator: '{k}'  threshold={t:.3f}  (FAR={far:.2f} clones accepted, FRR={frr:.2f} genuine rejected)")
    if k == "pop_score":
        print(f"-> set  KV_POP_MIN={t:.3f}  KV_POP=1   to enforce pop-noise liveness.")
    else:
        print(f"-> '{k}' separates best; wire it as the enforced feature in gates.liveness_gate,")
        print(f"   or use pop_score with its own threshold above. n is small — treat as directional.")
    if far > 0.1:
        print("WARNING: clones still leak at this threshold on full-band audio — combine with the "
              "device factor; consider a plosive-heavier prime and closer mic.")


if __name__ == "__main__":
    main()
