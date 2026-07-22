"""ECAPA-TDNN speaker embeddings — the Gate 3 engine.

speechbrain/spkrec-ecapa-voxceleb (Apache-2.0), 192-d L2-normalized vectors so
cosine similarity == dot product. This is a dedicated speaker space (unlike the
old wav2vec2 mean-pooled features in app/voiceprints.py), which is why Gate 3
can 1:1-verify a customer where the old CM could not.
"""
from __future__ import annotations

import os

import numpy as np
import torch

_MODEL = None
_CACHE = os.environ.get(
    "ECAPA_DIR", os.path.join(os.path.dirname(__file__), ".cache", "ecapa"))


def load():
    """Load (and on first run download, ~80 MB) the ECAPA encoder. Idempotent."""
    global _MODEL
    if _MODEL is None:
        from speechbrain.inference.speaker import EncoderClassifier
        _MODEL = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=_CACHE,
            run_opts={"device": "cpu"},
        )
    return _MODEL


def embed(wav16k: np.ndarray) -> np.ndarray:
    """Mono float32 waveform @16 kHz -> 192-d L2-normalized speaker embedding."""
    with torch.no_grad():
        t = torch.from_numpy(np.ascontiguousarray(wav16k, dtype=np.float32)).unsqueeze(0)
        e = load().encode_batch(t).squeeze().cpu().numpy().astype(np.float32)
    n = np.linalg.norm(e)
    return e / n if n > 0 else e


def score(enrolled: list[np.ndarray], probe: np.ndarray) -> float:
    """Speaker-match score = mean of the top-2 cosines vs the enrolled clips.

    Top-2 (not max, not mean-of-all) is robust to one weak enrollment clip
    without letting a single lucky match carry the decision."""
    if not enrolled:
        return 0.0
    sims = sorted((float(np.dot(e, probe)) for e in enrolled), reverse=True)
    return float(np.mean(sims[:2])) if len(sims) >= 2 else float(sims[0])
