"""Phase 2 acceptance self-check (MASTER-PLAN §8): the Gate 0 quality path
flags silence / clipping and passes real speech with the right reason codes. Run:
  ../.venv/Scripts/python.exe -m verify_app.selfcheck_quality      # from backend/
"""
from __future__ import annotations

import os

import numpy as np

from ml.audio_utils import load_audio
from verify_app import gates

_SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "sample_audio")
SR = 16000


def main() -> None:
    # (a) silence -> not ok, level/speech reason
    silent = gates.quality_gate(np.zeros(3 * SR, dtype=np.float32))
    print(f"silence      -> ok={silent['ok']} reason={silent['reason']}")
    assert not silent["ok"] and silent["reason"] in ("TOO_QUIET", "NO_SPEECH", "NO_AUDIO")

    # (b) full-scale noise -> not ok, clipping/noisy
    rng = np.random.default_rng(0)
    loud = np.clip(3.0 * rng.standard_normal(3 * SR), -1.0, 1.0).astype(np.float32)
    noisy = gates.quality_gate(loud)
    print(f"clipped noise-> ok={noisy['ok']} reason={noisy['reason']}")
    assert not noisy["ok"] and noisy["reason"] in ("CLIPPING", "NOISY")

    # (c) real speech -> ok, some speech seconds, trimmed
    wav, _ = load_audio(os.path.join(_SAMPLES, "chris_original.mp3"))
    wav = wav[: 14 * SR]                      # keep within DUR_MAX
    good = gates.quality_gate(wav)
    print(f"real speech  -> ok={good['ok']} reason={good['reason']} "
          f"speech_sec={good['scores']['speech_sec']} snr_db={good['scores']['snr_db']}")
    assert good["ok"], f"real speech should pass Gate 0, got {good['reason']}"
    assert good["scores"]["speech_sec"] >= 1.5
    assert len(good["wav"]) <= len(wav)       # trimmed (or equal)

    print("quality self-check ok")


if __name__ == "__main__":
    main()
