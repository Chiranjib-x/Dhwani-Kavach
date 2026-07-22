"""Digit ASR via faster-whisper tiny (int8, CPU) — feeds Gate 1.

`tiny` is plenty for reading 6 digits and stays ~1-2 s on the free 2-vCPU tier.
Greedy decode, English, no cross-segment conditioning (each clip is independent).
"""
from __future__ import annotations

import os

import numpy as np

_MODEL = None
_SIZE = os.environ.get("KV_WHISPER_SIZE", "tiny")   # upgrade knob: 'base' if tiny mishears accents


def load():
    """Load (first run downloads the tiny model) the faster-whisper model. Idempotent."""
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(
            _SIZE, device="cpu", compute_type="int8",
            download_root=os.environ.get("WHISPER_DIR",
                          os.path.join(os.path.dirname(__file__), ".cache", "whisper")))
    return _MODEL


def transcribe(wav16k: np.ndarray) -> str:
    """Mono float32 @16 kHz -> transcript text (segments joined)."""
    segments, _ = load().transcribe(
        np.ascontiguousarray(wav16k, dtype=np.float32),
        beam_size=1, language="en",
        condition_on_previous_text=False, temperature=0.0)
    return " ".join(s.text for s in segments).strip()
