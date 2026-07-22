"""Digit ASR via faster-whisper (int8, CPU) — feeds Gate 1.

`tiny` is fast (~1-2 s on 2 vCPU) but its multilingual accuracy is weak; for a
Hindi/regional deployment bump KV_WHISPER_SIZE to 'base' or 'small' if tiny
mishears the digits. Greedy decode, no cross-segment conditioning.

Language is AUTO-DETECTED by default (KV_ASR_LANG unset) so a caller reading the
OTP in Hindi/regional isn't transcribed as broken English -- the digit parser
(challenge.digits_from) already understands Hindi digits/words. Pin a language
via KV_ASR_LANG=hi (etc.) only if a single-language deployment finds auto-detect
flaky on short digit reads.
"""
from __future__ import annotations

import os

import numpy as np

_MODEL = None
_SIZE = os.environ.get("KV_WHISPER_SIZE", "tiny")   # upgrade knob: 'base'/'small' for Hindi/accents
_LANG = os.environ.get("KV_ASR_LANG", "").strip() or None   # None -> auto-detect (Hindi/regional)


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
        beam_size=1, language=_LANG,
        condition_on_previous_text=False, temperature=0.0)
    return " ".join(s.text for s in segments).strip()
