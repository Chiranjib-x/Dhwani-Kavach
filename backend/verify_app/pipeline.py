"""Decode + the 4-gate cascade. Pure logic: no sqlite, no HTTP.

`decode` turns uploaded bytes into a 16 kHz mono waveform (or a reason code).
`verify` and `enroll_slot` run the gates and return a partial verdict; api.py
owns session state (attempts, challenge rotation, lockout, audit, persistence)
and finalizes the response. This split keeps the security-relevant gate order in
one readable place and makes the cascade unit-testable without a running server.
"""
from __future__ import annotations

import numpy as np

from ml.audio_utils import load_audio_bytes
from verify_app import asr, challenge, config, gates, speaker


class DecodeError(Exception):
    """Raised with a reason code when uploaded bytes can't become audio."""


def decode(data: bytes) -> np.ndarray:
    if not data:
        raise DecodeError("NO_AUDIO")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise DecodeError("TOO_LONG")
    try:
        wav, _ = load_audio_bytes(data, 16000)
    except Exception as e:  # noqa: BLE001
        raise DecodeError("BAD_AUDIO_FORMAT") from e
    if wav is None or len(wav) == 0:
        raise DecodeError("NO_AUDIO")
    return wav.astype(np.float32)


def _blank_scores() -> dict:
    return {"quality": None, "content": None, "liveness": None, "speaker": None}


def verify(enrolled: list[np.ndarray], challenge_digits: str, attempts: int, wav: np.ndarray) -> dict:
    """Run Gates 0->3 in order, short-circuiting at the first decisive failure.

    Returns a partial verdict:
      verdict         ACCEPT | REJECT | STEP_UP | RETRY
      gate_failed     quality | content | liveness | speaker | None
      reasons         list of reason codes
      scores          per-gate score dicts (None until that gate runs)
      consume_attempt whether api.py should count this against MAX_ATTEMPTS
      rotate_challenge whether api.py should issue a fresh challenge
    """
    scores = _blank_scores()

    # Gate 0 — quality ALWAYS first. User-fixable, so a free RETRY (no attempt consumed).
    q = gates.quality_gate(wav)
    scores["quality"] = q["scores"]
    if not q["ok"]:
        return {"verdict": "RETRY", "gate_failed": "quality", "reasons": [q["reason"]],
                "scores": scores, "consume_attempt": False, "rotate_challenge": False}
    wav = q["wav"]

    last = attempts + 1 >= config.MAX_ATTEMPTS
    state = {"liveness_uncertain": False}

    def gate_content():
        # did they read THIS challenge? failing consumes an attempt + rotates the code.
        c = gates.content_gate(challenge_digits, asr.transcribe(wav))
        scores["content"] = c["scores"]
        if not c["ok"]:
            return {"verdict": "REJECT" if last else "RETRY", "gate_failed": "content",
                    "reasons": ["WRONG_PHRASE"] + (["TOO_MANY_ATTEMPTS"] if last else []),
                    "scores": scores, "consume_attempt": True, "rotate_challenge": not last}
        return None

    def gate_liveness():
        # soft: near-certain synthetic -> hard reject; borderline -> remembered (STEP_UP later).
        l = gates.liveness_gate(wav)
        scores["liveness"] = l["scores"]
        if l["band"] == "reject":
            return {"verdict": "REJECT", "gate_failed": "liveness", "reasons": ["SPOOF_SUSPECTED"],
                    "scores": scores, "consume_attempt": True, "rotate_challenge": False}
        state["liveness_uncertain"] = l["band"] == "borderline"
        return None

    def gate_speaker():
        sp = gates.speaker_gate(enrolled, wav)
        scores["speaker"] = sp["scores"]
        if sp["band"] == "reject":
            return {"verdict": "REJECT", "gate_failed": "speaker", "reasons": ["VOICE_MISMATCH"],
                    "scores": scores, "consume_attempt": True, "rotate_challenge": False}
        if sp["band"] == "borderline":
            # one RETRY, then STEP_UP (never a hard reject of a maybe-genuine caller)
            return {"verdict": "STEP_UP" if last else "RETRY", "gate_failed": "speaker",
                    "reasons": ["BORDERLINE_VOICE"], "scores": scores,
                    "consume_attempt": True, "rotate_challenge": not last}
        return None

    # Run the three gates in the configured order (KV_GATE_ORDER); first decisive
    # failure short-circuits. Quality is always first (above); order only reshuffles these.
    fns = {"content": gate_content, "liveness": gate_liveness, "speaker": gate_speaker}
    for name in config.GATE_ORDER:
        r = fns[name]()
        if r is not None:
            return r

    # All gates passed. Uncertain liveness downgrades ACCEPT -> STEP_UP.
    if state["liveness_uncertain"]:
        return {"verdict": "STEP_UP", "gate_failed": "liveness", "reasons": ["BORDERLINE_VOICE"],
                "scores": scores, "consume_attempt": True, "rotate_challenge": False}
    return {"verdict": "ACCEPT", "gate_failed": None, "reasons": [], "scores": scores,
            "consume_attempt": True, "rotate_challenge": False}


def enroll_slot(wav: np.ndarray) -> dict:
    """One enrollment clip: Gate 0 (quality) + Gate 2 (anti-spoof, blocks template
    poisoning) then embed. Returns {ok, reason, scores, embedding}."""
    scores = _blank_scores()
    q = gates.quality_gate(wav)
    scores["quality"] = q["scores"]
    if not q["ok"]:
        return {"ok": False, "reason": q["reason"], "scores": scores, "embedding": None}
    wav = q["wav"]

    l = gates.liveness_gate(wav)
    scores["liveness"] = l["scores"]
    if l["band"] == "reject":
        return {"ok": False, "reason": "SPOOF_SUSPECTED", "scores": scores, "embedding": None}

    emb = speaker.embed(wav)
    return {"ok": True, "reason": None, "scores": scores, "embedding": emb}


def enroll_consistency(embeddings: list[np.ndarray]) -> dict:
    """After all slots: every enroll clip must be the same voice. Returns
    {ok, min_pair, redo_slot} — redo_slot is the clip least like the others."""
    n = len(embeddings)
    if n < 2:
        return {"ok": True, "min_pair": 1.0, "redo_slot": None}
    mean_sims = []
    min_pair = 1.0
    for i in range(n):
        sims = [float(np.dot(embeddings[i], embeddings[j])) for j in range(n) if j != i]
        mean_sims.append(np.mean(sims))
        min_pair = min(min_pair, min(sims))
    ok = min_pair >= config.ENROLL_CONSISTENCY_MIN
    redo = None if ok else int(np.argmin(mean_sims))
    return {"ok": ok, "min_pair": round(float(min_pair), 3), "redo_slot": redo}
