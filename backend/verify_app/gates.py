"""The four verification gates. Each is a pure function: waveform (+context) in,
a small decision dict out. The cascade that chains them lives in pipeline.py.

Gate 0 (quality) reuses the existing ml.quality + ml.vad — NOT reimplemented.
Gates 1-3 delegate to challenge / liveness / speaker. Keeping them here as thin,
uniform functions makes the pipeline readable and each gate independently testable.
"""
from __future__ import annotations

import librosa
import numpy as np

from ml import quality, vad
from verify_app import challenge, config, liveness, popnoise, speaker

SR = 16000

# quality.assess reason text -> our stable reason code (frontend maps code->copy)
_QUALITY_CODES = (
    ("level", "TOO_QUIET"),
    ("clip", "CLIPPING"),
    ("noise", "NOISY"),
    ("no audio", "NO_AUDIO"),
)


def _quality_code(reason: str) -> str:
    low = reason.lower()
    for needle, code in _QUALITY_CODES:
        if needle in low:
            return code
    return "BAD_AUDIO_FORMAT"


def quality_gate(wav: np.ndarray) -> dict:
    """Gate 0: duration bounds + input quality + enough speech. Returns
    {ok, reason, scores, wav} where `wav` is trimmed of leading/trailing silence
    for the downstream model gates (both ECAPA and the CM behave better without
    seconds of padding)."""
    dur = len(wav) / SR
    speech_sec = round(vad.speech_ratio(wav) * dur, 2)
    q = quality.assess(wav, SR)
    scores = {"ok": q["ok"], "snr_db": q["snr_db"], "rms": q["rms"],
              "clip_frac": q["clip_frac"], "speech_sec": speech_sec, "duration_sec": round(dur, 2)}

    if dur < config.DUR_MIN_S:
        return {"ok": False, "reason": "TOO_SHORT", "scores": scores, "wav": wav}
    if dur > config.DUR_MAX_S:
        return {"ok": False, "reason": "TOO_LONG", "scores": scores, "wav": wav}
    if not q["ok"]:
        return {"ok": False, "reason": _quality_code(q["reason"]), "scores": scores, "wav": wav}
    if speech_sec < config.SPEECH_MIN_S:
        return {"ok": False, "reason": "NO_SPEECH", "scores": scores, "wav": wav}

    trimmed, _ = librosa.effects.trim(wav, top_db=30)
    if len(trimmed) < SR * 0.5:          # trim ate almost everything -> keep original
        trimmed = wav
    return {"ok": True, "reason": None, "scores": scores, "wav": trimmed.astype(np.float32)}


def content_gate(expected: str, transcript: str) -> dict:
    """Gate 1: did the caller read the challenge digits?"""
    r = challenge.content_ok(expected, transcript)
    return {"ok": r["ok"], "reason": None if r["ok"] else "WRONG_PHRASE", "scores": r}


def liveness_gate(wav: np.ndarray) -> dict:
    """Gate 2 (SOFT): live-human vs synthetic/replayed. Two independent signals:
      - CM bonafide (synthesis artifacts) — soft, over-flags genuine, so borderline
        -> STEP_UP not reject.
      - pop-noise / near-field (physical replay defense) — a loudspeaker can't make
        the low-frequency breath pop of a live near-field voice, so this catches a
        clone PLAYED THROUGH A SPEAKER regardless of clone quality.
    pop is REPORT-ONLY until calibrated (config.POP_ENFORCE); when enforced, a low
    pop score is a hard REJECT (REPLAY_SUSPECTED) — that's the over-the-air clone."""
    p = liveness.bonafide_p(wav)
    pop = popnoise.pop_score(wav)
    scores = {"bonafide_p": round(p, 3), "pop_p": round(pop, 3),
              "ok": p >= config.CM_BONAFIDE_OK}

    if config.POP_ENFORCE and pop < config.POP_MIN:
        scores["ok"] = False
        return {"ok": False, "reason": "REPLAY_SUSPECTED", "scores": scores, "band": "reject"}
    if p >= config.CM_BONAFIDE_OK:
        return {"ok": True, "reason": None, "scores": scores, "band": "pass"}
    if p < config.CM_BONAFIDE_REJECT:
        return {"ok": False, "reason": "SPOOF_SUSPECTED", "scores": scores, "band": "reject"}
    return {"ok": False, "reason": "BORDERLINE_VOICE", "scores": scores, "band": "borderline"}


def speaker_gate(enrolled: list[np.ndarray], probe_wav: np.ndarray) -> dict:
    """Gate 3: does the probe match the enrolled voiceprints? Three outcomes:
      accept     (score >= ASV_ACCEPT)
      reject     (score <= ASV_REJECT)
      borderline (in between -> retry / step-up)."""
    probe = speaker.embed(probe_wav)
    s = speaker.score(enrolled, probe)
    scores = {"cosine": round(s, 3), "ok": s >= config.ASV_ACCEPT}
    if s >= config.ASV_ACCEPT:
        return {"ok": True, "reason": None, "scores": scores, "band": "accept", "embedding": probe}
    if s <= config.ASV_REJECT:
        return {"ok": False, "reason": "VOICE_MISMATCH", "scores": scores, "band": "reject", "embedding": probe}
    return {"ok": False, "reason": "BORDERLINE_VOICE", "scores": scores, "band": "borderline", "embedding": probe}
