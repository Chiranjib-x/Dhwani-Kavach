"""Phase 5 acceptance self-check (MASTER-PLAN §8).

Real human clips must score higher bona-fide than their voice CLONES. Uses the
labeled original/clone pairs in sample_audio/. Asserts mean(real) > mean(clone)
(robust to the CMs' known per-clip over-flagging of genuine speech — see
MASTER-PLAN §4) and prints every score + latency + which CM backend ran, so the
separation and the false-positive risk are both visible.

  KV_CM=aasist ../.venv/Scripts/python.exe -m verify_app.selfcheck_liveness   # fast, no XLS-R
  ../.venv/Scripts/python.exe -m verify_app.selfcheck_liveness                 # default: cotrain
"""
from __future__ import annotations

import os
import time

import numpy as np

from ml.audio_utils import load_audio
from verify_app import config, liveness

_SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "sample_audio")

# (real_file, clone_file) pairs that exist in sample_audio/
_PAIRS = [
    ("chris_original.mp3", "chris_clone.mp3"),
    ("lily_original.mp3", "lilly_clone.mp3"),
    ("Script_5.mp3", "Script_5_clone.mp3.mpeg"),
]


def _bp(name: str) -> float:
    wav, _ = load_audio(os.path.join(_SAMPLES, name))
    return liveness.bonafide_p(wav)


def main() -> None:
    print(f"CM backend: warming '{config.KV_CM}'…")
    liveness.load()
    print(f"CM backend active: {liveness.backend_name()}")

    reals, clones, t0 = [], [], time.time()
    for real, clone in _PAIRS:
        try:
            r, c = _bp(real), _bp(clone)
        except FileNotFoundError as e:
            print(f"  skip pair ({e})"); continue
        reals.append(r); clones.append(c)
        flag = "  <-- genuine over-flagged" if r < 0.5 else ""
        print(f"  {real:28s} bonafide={r:.3f}   |   {clone:28s} bonafide={c:.3f}{flag}")
    dt = (time.time() - t0) / max(1, len(reals) + len(clones))

    mr, mc = float(np.mean(reals)), float(np.mean(clones))
    print(f"mean bonafide  real={mr:.3f}  clone={mc:.3f}  (gap={mr - mc:+.3f})")
    print(f"avg latency/clip: {dt*1000:.0f} ms")
    print(f"config: CM_BONAFIDE_OK={config.CM_BONAFIDE_OK} CM_BONAFIDE_REJECT={config.CM_BONAFIDE_REJECT} "
          "(both get recalibrated in Phase 7)")

    assert mr > mc, f"CM failed: real ({mr:.3f}) must beat clone ({mc:.3f}) on average"
    print("liveness self-check ok")


if __name__ == "__main__":
    main()
