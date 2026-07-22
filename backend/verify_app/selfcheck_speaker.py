"""Phase 3 acceptance self-check (MASTER-PLAN §8).

Proves the pivot thesis on real audio:
  1. two clips of the SAME speaker score HIGH cosine,
  2. a DIFFERENT speaker scores lower,
  3. store round-trips a vector byte-identically,
  4. first embed() after load() is < 3 s.

Bonus (printed, not asserted): how close a voice CLONE lands to the original —
the honest number behind the "can't be mimicked" claim (MASTER-PLAN §1). Run:
  ../.venv/Scripts/python.exe -m verify_app.selfcheck_speaker      # from backend/
"""
from __future__ import annotations

import os
import tempfile
import time
import uuid

import numpy as np

from ml.audio_utils import load_audio
from verify_app import config, speaker, store

_SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "sample_audio")


def _load(name: str) -> np.ndarray:
    wav, _ = load_audio(os.path.join(_SAMPLES, name))
    return wav


def main() -> None:
    print("loading ECAPA (first run downloads ~80 MB)…")
    speaker.load()

    chris = _load("chris_original.mp3")
    lily = _load("lily_original.mp3")
    half = len(chris) // 2

    t0 = time.time()
    e_chris_a = speaker.embed(chris[:half])      # same speaker, first half
    dt = time.time() - t0
    e_chris_b = speaker.embed(chris[half:])      # same speaker, second half
    e_lily = speaker.embed(lily)                 # different speaker

    same = speaker.score([e_chris_a], e_chris_b)
    diff = speaker.score([e_chris_a], e_lily)
    print(f"same-speaker cosine (Chris vs Chris): {same:.3f}")
    print(f"diff-speaker cosine (Chris vs Lily):  {diff:.3f}")
    print(f"first embed() latency: {dt*1000:.0f} ms")

    # bonus: clone-vs-original — informational, the honest "un-cloneable?" number
    try:
        e_chris_clone = speaker.embed(_load("chris_clone.mp3"))
        print(f"[clone] Chris real vs Chris CLONE cosine: "
              f"{speaker.score([e_chris_a], e_chris_clone):.3f}  "
              f"(> ASV_ACCEPT={config.ASV_ACCEPT} means the clone would pass Gate 3 alone — "
              f"this is exactly why Gates 1+2 exist)")
    except Exception as e:  # noqa: BLE001
        print(f"[clone] skipped: {e}")

    assert same > diff, f"same-speaker ({same:.3f}) must exceed diff-speaker ({diff:.3f})"
    assert same > 0.30, f"same-speaker cosine unexpectedly low ({same:.3f}) — check preprocessing"
    assert dt < 3.0, f"first embed() too slow ({dt:.2f}s)"

    # store round-trip: bytes must survive sqlite unchanged
    config.__dict__["DB_PATH"] = os.path.join(tempfile.gettempdir(), f"kv_sc_{uuid.uuid4().hex}.db")
    store._conn = None  # force reopen at the temp path
    store.create_user("u1")
    store.add_embedding("u1", 0, e_chris_a, "{}")
    got = store.get_embeddings("u1")[0]
    assert np.array_equal(got, e_chris_a), "embedding did not round-trip byte-identically"

    print("speaker self-check ok")


if __name__ == "__main__":
    main()
