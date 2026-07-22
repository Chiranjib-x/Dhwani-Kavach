"""Phase 4 acceptance self-check (MASTER-PLAN §8).

Hard-asserts the deterministic Gate 1 logic (digit extraction, homophones, edit
distance, content_ok) and runs faster-whisper on a real sample clip to prove the
ASR path loads and transcribes. Exact digit ACCURACY across accents is a Phase 7
calibration item (needs the team's own recordings), not asserted here. Run:
  ../.venv/Scripts/python.exe -m verify_app.selfcheck_challenge      # from backend/
"""
from __future__ import annotations

import os

from ml.audio_utils import load_audio
from verify_app import asr, challenge

_SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "sample_audio")


def main() -> None:
    # --- deterministic logic (the real risk surface) ---
    assert challenge.digits_from("four seven 2 nine oh three") == "472903"
    assert challenge.digits_from("for to ate") == "428"            # homophones
    assert challenge.digits_from("my code is 8 8 zero one") == "8801"
    assert challenge.digits_from("no numbers here") == ""
    assert challenge.edit_distance("472903", "472903") == 0
    assert challenge.edit_distance("472903", "472913") == 1        # one wrong digit
    assert challenge.edit_distance("472903", "47293") == 1         # one dropped digit

    assert challenge.content_ok("472903", "four seven two nine zero three")["ok"]
    assert challenge.content_ok("472903", "four seven two nine one three", max_edits=1)["ok"]  # 1 edit tolerated
    assert not challenge.content_ok("472903", "four seven two nine one four", max_edits=1)["ok"]  # 2 edits rejected

    c = challenge.new_challenge()
    assert len(c) == 6 and c.isdigit(), f"bad challenge {c!r}"
    print("digit/challenge logic ok")

    # --- ASR path: real model on real speech, transcript must be non-empty ---
    print("loading faster-whisper tiny (first run downloads)…")
    asr.load()
    wav, _ = load_audio(os.path.join(_SAMPLES, "Script_5.mp3"))
    text = asr.transcribe(wav)
    print(f"ASR transcript (Script_5.mp3): {text!r}")
    print(f"digits heard: {challenge.digits_from(text)!r}")
    assert text, "ASR returned empty transcript on real speech — the whisper path is broken"

    print("challenge self-check ok")


if __name__ == "__main__":
    main()
