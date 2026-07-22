"""Spoken-digit challenge — issue + verify.

The verify leg is what makes this a USE CASE and not just a prompt: the caller
must speak the digits (ASR content match) AND the voice must pass the deepfake
ensemble. A pre-recorded clone fails the content check (wrong/no digits); a
live TTS rig that answers correctly still faces the synthetic-voice check.
This is the "voice OTP" / passive-auth pattern (app unlock, payment OTP,
call-centre step-up) with the anti-spoof layer those flows are missing.
"""
import asyncio
import re
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ml.liveness import generate_challenge
from ml.audio_utils import load_audio_bytes
from ml.detector import detect_samples
from ml import scam_detector

router = APIRouter()

# challenge_id -> (digits, issued_at). In-memory, single-process — demo scale.
_pending: dict[str, tuple[list[int], float]] = {}
_TTL_S = 300
_MAX_PENDING = 1000

_WORD2DIGIT = {"zero": "0", "oh": "0", "o": "0", "one": "1", "two": "2", "to": "2",
               "too": "2", "three": "3", "four": "4", "for": "4", "five": "5",
               "six": "6", "seven": "7", "eight": "8", "ate": "8", "nine": "9"}


def _spoken_digits(text: str) -> str:
    """Digits in spoken order: literal digits plus english digit-words."""
    out = []
    for tok in re.findall(r"[0-9]|[a-zA-Z]+", text.lower()):
        if tok.isdigit():
            out.append(tok)
        elif tok in _WORD2DIGIT:
            out.append(_WORD2DIGIT[tok])
    return "".join(out)


@router.get("/challenge")
async def get_challenge():
    """Return a spoken-digit liveness challenge for the caller."""
    ch = generate_challenge()
    now = time.time()
    if len(_pending) >= _MAX_PENDING:  # drop expired, then oldest
        for k in [k for k, (_, ts) in _pending.items() if now - ts > _TTL_S]:
            _pending.pop(k, None)
    _pending[ch["challenge_id"]] = (ch["digits"], now)
    return ch


@router.post("/challenge/verify")
async def verify_challenge(challenge_id: str = Form(...), audio: UploadFile = File(...)):
    """Verify a challenge response: content match (ASR) + synthetic-voice check."""
    entry = _pending.get(challenge_id)
    if entry is None or time.time() - entry[1] > _TTL_S:
        raise HTTPException(status_code=404, detail="Unknown or expired challenge.")
    expected = "".join(map(str, entry[0]))

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty audio upload.")
    try:
        samples, _ = await asyncio.to_thread(load_audio_bytes, data)
        (text, lang), det = await asyncio.gather(
            asyncio.to_thread(scam_detector.transcribe, samples),
            asyncio.to_thread(detect_samples, samples),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    heard = _spoken_digits(text)
    digits_ok = expected in heard  # tolerate leading/trailing chatter
    # A suspected loudspeaker replay (see ml/replay.py) can still read a clean
    # deepfake score -- the neural detector wasn't trained on that channel --
    # so a correct-but-replayed answer must not pass just because the voice
    # score looks fine on it.
    replay_suspect = det.get("replay", {}).get("suspect", False)
    voice_ok = det["alert_level"] in ("GREEN", "AMBER") and not replay_suspect
    passed = digits_ok and voice_ok
    _pending.pop(challenge_id, None)  # single use

    if not digits_ok:
        reason = "challenge digits not spoken correctly — possible replayed/pre-recorded audio"
    elif replay_suspect:
        reason = "loudspeaker replay suspected — correct digits, untrusted channel"
    elif not voice_ok:
        reason = ("synthetic voice detected — correct answer, wrong speaker type"
                  if det["alert_level"] == "RED" else "input quality too low to trust")
    else:
        reason = "live human, correct response"
    return {
        "passed": passed, "reason": reason,
        "digits_expected": expected, "digits_heard": heard, "transcript": text,
        "language": lang, "alert_level": det["alert_level"],
        "risk_score": det["risk_score"], "replay": det.get("replay", {}),
    }
