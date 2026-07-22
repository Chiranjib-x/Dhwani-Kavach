"""ECAPA-TDNN speaker embeddings — the Gate 3 engine.

speechbrain/spkrec-ecapa-voxceleb (Apache-2.0), 192-d L2-normalized vectors so
cosine similarity == dot product. This is a dedicated speaker space (unlike the
old wav2vec2 mean-pooled features in app/voiceprints.py), which is why Gate 3
can 1:1-verify a customer where the old CM could not.
"""
from __future__ import annotations

import os
import pathlib
import shutil

import numpy as np
import torch

_MODEL = None
_REPO = "speechbrain/spkrec-ecapa-voxceleb"
_CACHE = os.environ.get(
    "ECAPA_DIR", os.path.join(os.path.dirname(__file__), ".cache", "ecapa"))

_symlink_patched = False


def _patch_symlink_fallback() -> None:
    """Make a denied symlink fall back to a copy. Idempotent, process-wide.

    speechbrain collects the ECAPA checkpoints into savedir by SYMLINKing from
    the HF cache, and from_hparams gives no way to turn that off (its
    local_strategy isn't forwarded to the checkpoint-collection step). On Windows
    a symlink needs Developer Mode / admin, so the first load dies with WinError
    1314 for anyone without it -- including the demo box. We wrap
    pathlib.Path.symlink_to so a failed symlink becomes shutil.copy. It only
    changes behaviour when a symlink would have FAILED (strictly safer), and never
    triggers on Linux/macOS where the symlink succeeds.
    ponytail: a syscall shim beats making every operator flip a Windows security
    setting; drop it if speechbrain ever forwards a copy strategy to collect_files.
    """
    global _symlink_patched
    if _symlink_patched:
        return
    _orig = pathlib.Path.symlink_to

    def _symlink_or_copy(self, target, target_is_directory=False):
        try:
            return _orig(self, target, target_is_directory)
        except OSError:
            shutil.copy(str(target), str(self))

    pathlib.Path.symlink_to = _symlink_or_copy
    _symlink_patched = True


def load():
    """Load (and on first run download, ~80 MB) the ECAPA encoder. Idempotent."""
    global _MODEL
    if _MODEL is None:
        _patch_symlink_fallback()
        from speechbrain.inference.speaker import EncoderClassifier
        _MODEL = EncoderClassifier.from_hparams(
            source=_REPO,
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
