"""Scam-script layer — catch the vishing where the voice is a *real human*.

Pipeline: audio -> transcript (faster-whisper, optional) -> LLM (NVIDIA NIM /
Nemotron) -> scam score + detected social-engineering tactics.

Everything degrades gracefully: no whisper, no API key, or any network error ->
returns a neutral {score:0, tactics:[]} so the rest of the pipeline is never
blocked. The deepfake detector keeps working regardless.

Uses stdlib urllib for the LLM call (no new HTTP dependency).
ponytail: whisper "base" + 8s LLM timeout; raise model size / timeout only if accuracy or latency demands it.
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np

from ml.audio_utils import SAMPLE_RATE

_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
_MODEL = os.environ.get("NVIDIA_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
_KEY = os.environ.get("NVIDIA_API_KEY", "")

_TACTICS = [
    "urgency", "authority_impersonation", "isolation",
    "new_beneficiary", "sensitive_info_request", "threat",
]

_SYSTEM = (
    "You are a bank fraud analyst. Given a phone-call transcript, rate how likely "
    "it is a social-engineering / vishing scam from 0 to 100, and list ONLY the "
    "tactics with EXPLICIT evidence in the transcript. Do not infer or guess a "
    "tactic that is not actually said. Tactic definitions:\n"
    "- urgency: pressure to act immediately / time limit / 'right now'.\n"
    "- authority_impersonation: claims to be bank/police/govt/official.\n"
    "- isolation: tells the person not to tell anyone / stay on the line.\n"
    "- new_beneficiary: asks to transfer/send money to a new or unknown account.\n"
    "- sensitive_info_request: explicitly asks for OTP, PIN, password, CVV, or card number.\n"
    "- threat: threatens account freeze, arrest, penalty, or loss.\n"
    "Include a tactic only if its definition is clearly met by the words in the "
    'transcript. Reply with STRICT JSON only: {"score": <int 0-100>, "tactics": [<strings>]}. '
    "No prose."
)

# --- transcription (optional) ------------------------------------------------
_whisper = None
_whisper_tried = False


def _get_whisper():
    global _whisper, _whisper_tried
    if _whisper_tried:
        return _whisper
    _whisper_tried = True
    try:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2)
    except Exception:
        _whisper = None  # not installed / failed to load -> scam layer stays neutral
    return _whisper


def transcribe(audio: np.ndarray) -> tuple[str, str]:
    """Return (transcript, detected_language). Language auto-detected (Hindi/
    English/Hinglish/regional all supported by Whisper)."""
    model = _get_whisper()
    if model is None:
        return "", ""
    try:
        segments, info = model.transcribe(audio.astype("float32"), language=None, vad_filter=True)
        text = " ".join(s.text for s in segments).strip()
        return text, getattr(info, "language", "") or ""
    except Exception:
        return "", ""


# --- LLM scoring -------------------------------------------------------------
def score_transcript(text: str) -> dict:
    """Score a transcript via NIM. Neutral result on any failure."""
    text = (text or "").strip()
    if not text or not _KEY:
        return {"score": 0, "tactics": [], "transcript": text}
    try:
        payload = json.dumps({
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": text[:4000]},
            ],
            "temperature": 0.0,
            "max_tokens": 200,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{_BASE_URL}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        score = int(np.clip(parsed.get("score", 0), 0, 100))
        tactics = [t for t in parsed.get("tactics", []) if t in _TACTICS]
        return {"score": score, "tactics": tactics, "transcript": text}
    except Exception:
        return {"score": 0, "tactics": [], "transcript": text}


def _extract_json(s: str) -> dict:
    """Pull the first {...} block out of an LLM reply; tolerate stray prose/fences."""
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1:
        return {}
    try:
        return json.loads(s[i:j + 1])
    except Exception:
        return {}


def analyze(audio: np.ndarray) -> dict:
    """audio -> transcript -> scam score. Neutral if transcription/LLM unavailable."""
    text, lang = transcribe(audio)
    result = score_transcript(text)
    result["language"] = lang
    return result


if __name__ == "__main__":
    # ponytail self-check: parser + scoring logic without needing the network.
    assert _extract_json('noise {"score": 88, "tactics": ["urgency"]} tail') == {
        "score": 88, "tactics": ["urgency"]}
    assert _extract_json("not json") == {}
    r = score_transcript("")            # empty -> neutral
    assert r["score"] == 0 and r["tactics"] == []
    print("scam_detector self-check ok")
