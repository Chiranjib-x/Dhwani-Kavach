"""Gate 2 liveness adapter — anti-spoof CM, exposed as a bona-fide probability.

Wraps the EXISTING detectors in backend/ml/ (read those; not reimplemented here):
  KV_CM=cotrain -> ml.detector_v2  (W2VAASIST + truncated XLS-R; champion in-repo,
                    catches synthetic near-perfectly but over-flags genuine — the
                    reason Gate 2 is a SOFT gate; see MASTER-PLAN §4)
  KV_CM=sls     -> ml.detector_v4  (full XLS-R + SLS head; documented best
                    generalization to real-world varied-mic audio — the live-mic
                    channel. Heavier: 1.35 GB weights, slower on CPU. A/B in Phase 7)
  KV_CM=aasist  -> ml.aasist_model (raw AASIST; tiny + fast, no XLS-R backbone —
                    the free-tier fallback if XLS-R is too slow/large)

All three expose spoof probability in [0,1] (higher = more likely fake), so:
    bonafide_p = 1 - spoof_p
The soft-gate decision policy lives in gates.py / pipeline.py — this module only
produces the number. Input is truncated to CM_MAX_SECONDS first (CPU win; the
CMs internally repeat-pad to ~4 s anyway, so nothing is lost by capping).
"""
from __future__ import annotations

import os

import numpy as np

from verify_app import config

_backend = None          # ("cotrain"|"sls"|"aasist", callable spoof_prob fn)


def _resolve():
    """Pick the CM backend from KV_CM, falling back to whatever is actually
    loadable so the server never dies because one checkpoint is missing."""
    choice = config.KV_CM.lower()

    if choice == "sls":
        from ml import detector_v4
        if detector_v4.available():
            return "sls", detector_v4.infer
    if choice == "aasist" or choice == "sls":  # aasist explicitly, or sls-not-present fallthrough
        from ml.aasist_model import load_aasist, infer as _ai
        path = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
        model = load_aasist(path)
        return "aasist", (lambda wav: _ai(model, wav))

    # default: cotrain
    from ml import detector_v2
    if detector_v2.available():
        return "cotrain", detector_v2.infer
    # last-resort fallback: raw AASIST always ships in the repo
    from ml.aasist_model import load_aasist, infer as _ai
    path = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")
    model = load_aasist(path)
    return "aasist", (lambda wav: _ai(model, wav))


def load():
    """Warm the selected CM (first cotrain/sls call downloads XLS-R ~1.2 GB). Idempotent."""
    global _backend
    if _backend is None:
        _backend = _resolve()
    return _backend


def backend_name() -> str:
    return load()[0]


def _truncate(wav16k: np.ndarray) -> np.ndarray:
    cap = int(config.CM_MAX_SECONDS * 16000)
    return wav16k[:cap] if len(wav16k) > cap else wav16k


def bonafide_p(wav16k: np.ndarray) -> float:
    """Probability the clip is a live human voice (not TTS/VC), in [0,1].
    Higher = more likely genuine. Gate 2's soft thresholds live in config."""
    _, spoof_fn = load()
    x = np.ascontiguousarray(_truncate(wav16k), dtype=np.float32)
    spoof = float(spoof_fn(x))
    return float(np.clip(1.0 - spoof, 0.0, 1.0))
