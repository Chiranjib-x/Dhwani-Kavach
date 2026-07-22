"""HTTP layer: sessions, enrollment, verification, admin. Owns all session state
(attempts, challenge rotation, lockout, audit); the gate logic lives in pipeline.py.
"""
from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from verify_app import challenge, config, pipeline, store

router = APIRouter(prefix="/v2")


def _capture(wav, user_id: str, verdict: str) -> None:
    """Save a verified clip to disk when KEEP_AUDIO=1 — red-team sample collection
    (Tier-1 tuning). No-op in production."""
    if not config.KEEP_AUDIO:
        return
    try:
        import soundfile as sf
        os.makedirs(config.CAPTURE_DIR, exist_ok=True)
        fn = f"{time.strftime('%Y%m%dT%H%M%S')}_{user_id}_{verdict}.wav"
        sf.write(os.path.join(config.CAPTURE_DIR, fn), wav, 16000, subtype="PCM_16")
    except Exception:  # noqa: BLE001 — capture must never break a verdict
        pass


# --- helpers -------------------------------------------------------------- #

def _err(code: str, status: int = 200) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status)


def _verdict(verdict: str, gate_failed=None, reasons=None, scores=None,
             attempts_left=None, new_challenge=None, extra=None) -> dict:
    out = {"verdict": verdict, "gate_failed": gate_failed, "reasons": reasons or [],
           "scores": scores or {"quality": None, "content": None, "liveness": None, "speaker": None}}
    if attempts_left is not None:
        out["attempts_left"] = attempts_left
    if new_challenge is not None:
        out["new_challenge"] = new_challenge
    if extra:
        out.update(extra)
    return out


def _session_problem(sess: dict | None, mode: str) -> str | None:
    if sess is None:
        return "SESSION_EXPIRED"          # unknown id -> treat as gone
    if sess["mode"] != mode:
        return "SESSION_USED"
    if sess["done"]:
        return "SESSION_USED"
    if sess["expires_at"] < time.time():
        return "SESSION_EXPIRED"
    return None


# --- session ------------------------------------------------------------- #

@router.post("/session")
def create_session(body: dict):
    user_id = (body.get("user_id") or "").strip()
    mode = body.get("mode")
    if not user_id or mode not in ("enroll", "verify", "reenroll"):
        return _err("BAD_REQUEST", 400)

    if mode == "enroll":
        store.create_user(user_id, body.get("display_name"))
        if store.get_user(user_id)["enrolled"]:
            return _err("ALREADY_ENROLLED")
        s = store.create_session(user_id, "enroll", None)
        return {"session_id": s["session_id"], "mode": "enroll",
                "expires_at": s["expires_at"], "prompts": config.ENROLL_PROMPTS}

    # verify + reenroll are both voice-gated flows: they issue a one-time digit
    # challenge and check it against the enrolled voiceprint. reenroll then also
    # captures the accepted clips as the NEW voiceprint (retraining), which is why
    # it needs to prove identity first — the voice itself authorizes the overwrite.
    user = store.get_user(user_id)
    if not user or not user["enrolled"]:
        return _err("NOT_ENROLLED")
    if store.check_lockout(user_id):
        return _err("LOCKED")
    # randomize: body override (testing) falls back to the global config default
    randomize = bool(body.get("randomize", config.RANDOMIZE))
    randomize_prime = bool(body.get("randomize_prime", config.RANDOMIZE_PRIME))
    ch = challenge.new_challenge(randomize=randomize)
    s = store.create_session(user_id, mode, ch, randomize=randomize)
    out = {"session_id": s["session_id"], "mode": mode,
           "expires_at": s["expires_at"], "challenge": ch, "randomize": randomize,
           "prime": challenge.new_prime(randomize=randomize_prime),
           "randomize_prime": randomize_prime}
    if mode == "reenroll":
        out["slots_total"] = config.ENROLL_SLOTS
    return out


# --- audio (enroll slot, reenroll slot, or verify) ------------------------ #

@router.post("/audio")
async def audio(session_id: str = Form(...), slot: int = Form(0),
                file: UploadFile = File(...),
                x_test_label: str | None = Header(None)):
    sess = store.get_session(session_id)
    if sess is None:
        return _verdict("REJECT", reasons=["SESSION_EXPIRED"])

    data = await file.read()
    try:
        wav = pipeline.decode(data)
    except pipeline.DecodeError as e:
        # decode failure never consumes an attempt (bad upload != auth attempt)
        return _verdict("RETRY", reasons=[str(e)])

    if sess["mode"] == "enroll":
        return _enroll(sess, slot, wav, x_test_label)
    if sess["mode"] == "reenroll":
        return _reenroll(sess, slot, wav, x_test_label)
    return _verify(sess, wav, x_test_label)


def _verify(sess: dict, wav, label: str | None) -> dict:
    problem = _session_problem(sess, "verify")
    if problem:
        return _verdict("REJECT", reasons=[problem])
    user_id = sess["user_id"]
    if store.check_lockout(user_id):
        return _verdict("LOCKED", reasons=["LOCKED"])
    if sess["attempts"] >= config.MAX_ATTEMPTS:
        store.finish_session(sess["session_id"])
        return _verdict("REJECT", reasons=["TOO_MANY_ATTEMPTS"])

    enrolled = store.get_embeddings(user_id)
    if not enrolled:
        return _verdict("REJECT", reasons=["NOT_ENROLLED"])

    r = pipeline.verify(enrolled, sess["challenge"], sess["attempts"], wav)
    scores = r["scores"]
    reasons = list(r["reasons"])
    verdict, gate_failed = r["verdict"], r["gate_failed"]

    new_challenge = None
    if r["consume_attempt"]:
        # rotate using this session's randomize setting (fixed stays fixed in testing)
        new_challenge = challenge.new_challenge(randomize=sess["randomize"]) if r["rotate_challenge"] else None
        store.bump_attempt(sess["session_id"], new_challenge)
    attempts_after = sess["attempts"] + (1 if r["consume_attempt"] else 0)

    if verdict in ("ACCEPT", "REJECT", "STEP_UP"):
        store.finish_session(sess["session_id"])
        if verdict == "ACCEPT":
            store.clear_fails(user_id)
        elif verdict == "REJECT":
            store.record_fail(user_id)

    _capture(wav, user_id, verdict)
    store.log_audit(user_id, sess["session_id"], "verify", verdict,
                    gate_failed, json.dumps(scores), label)
    return _verdict(verdict, gate_failed, reasons, scores,
                    attempts_left=max(0, config.MAX_ATTEMPTS - attempts_after),
                    new_challenge=new_challenge)


def _enroll(sess: dict, slot: int, wav, label: str | None) -> dict:
    problem = _session_problem(sess, "enroll")
    if problem:
        return _verdict("REJECT", reasons=[problem])
    user_id = sess["user_id"]
    if not (0 <= slot < config.ENROLL_SLOTS):
        return _verdict("RETRY", reasons=["BAD_REQUEST"])

    r = pipeline.enroll_slot(wav)
    if not r["ok"]:
        store.log_audit(user_id, sess["session_id"], "enroll", "RETRY", None,
                        json.dumps(r["scores"]), label)
        return _verdict("RETRY", gate_failed=("liveness" if r["reason"] == "SPOOF_SUSPECTED" else "quality"),
                        reasons=[r["reason"]], scores=r["scores"])

    store.add_embedding(user_id, slot, r["embedding"], json.dumps(r["scores"]["quality"]))
    filled = store.mark_slot_filled(sess["session_id"], slot)

    # All slots filled IN THIS SESSION -> consistency check + finalize. Judged by
    # filled_slots, not by counting the user's total stored embeddings.
    if len(filled) >= config.ENROLL_SLOTS:
        embs = store.get_embeddings(user_id)
        con = pipeline.enroll_consistency(embs)
        if not con["ok"]:
            store.log_audit(user_id, sess["session_id"], "enroll", "RETRY", "speaker",
                            json.dumps({"consistency": con}), label)
            return _verdict("RETRY", gate_failed="speaker", reasons=["ENROLL_INCONSISTENT"],
                            scores=r["scores"], extra={"redo_slot": con["redo_slot"], "consistency": con})
        store.mark_enrolled(user_id)
        store.finish_session(sess["session_id"])
        store.log_audit(user_id, sess["session_id"], "enroll", "ENROLLED", None,
                        json.dumps({"consistency": con}), label)
        return _verdict("ENROLLED", scores=r["scores"], extra={"consistency": con})

    store.log_audit(user_id, sess["session_id"], "enroll", "ENROLL_SLOT_OK", None,
                    json.dumps(r["scores"]), label)
    return _verdict("ENROLL_SLOT_OK", scores=r["scores"],
                    extra={"slots_done": len(filled), "slots_total": config.ENROLL_SLOTS})


def _reenroll(sess: dict, slot: int, wav, label: str | None) -> dict:
    """Retrain an existing user's voiceprint (voice changed with age/illness, a
    noisy original enrollment, a new mic) WITHOUT creating a new identity.

    Authorized BY the voice itself: every new clip must first pass a full
    verification (quality + phrase + liveness + speaker match) against the CURRENT
    voiceprint before it is captured. So only the enrolled customer, reading a
    fresh one-time code live, can overwrite their own print — a clip that doesn't
    match the enrolled voice (or a replayed recording that reads the wrong code)
    is refused and nothing changes. A voice that has drifted too far to match at
    all must go through the admin reset-enrollment escape hatch.
    """
    problem = _session_problem(sess, "reenroll")
    if problem:
        return _verdict("REJECT", reasons=[problem])
    user_id = sess["user_id"]
    if store.check_lockout(user_id):
        return _verdict("LOCKED", reasons=["LOCKED"])
    if not (0 <= slot < config.ENROLL_SLOTS):
        return _verdict("RETRY", reasons=["BAD_REQUEST"])

    current = store.get_embeddings(user_id)      # the print being replaced = the authorizer
    if not current:
        return _verdict("REJECT", reasons=["NOT_ENROLLED"])

    # Authorize this clip against the current voiceprint. attempts=0: judge THIS
    # clip on its own merits (no lockout / last-attempt step-up) — a retrain slot
    # can be re-recorded freely, it isn't a login attempt.
    auth = pipeline.verify(current, sess["challenge"], 0, wav)
    if auth["verdict"] != "ACCEPT":
        # not proven to be the enrolled customer on this clip -> capture nothing,
        # rotate the code, let them re-record this slot.
        new_ch = challenge.new_challenge(randomize=sess["randomize"])
        store.bump_attempt(sess["session_id"], new_ch)
        store.log_audit(user_id, sess["session_id"], "reenroll", "RETRY",
                        auth["gate_failed"], json.dumps(auth["scores"]), label)
        return _verdict("RETRY", gate_failed=auth["gate_failed"],
                        reasons=auth["reasons"] or ["VOICE_UNVERIFIED"],
                        scores=auth["scores"], new_challenge=new_ch)

    # authorized -> capture this clip as a fresh enrollment embedding
    e = pipeline.enroll_slot(wav)
    if not e["ok"]:
        return _verdict("RETRY", gate_failed=("liveness" if e["reason"] == "SPOOF_SUSPECTED" else "quality"),
                        reasons=[e["reason"]], scores=e["scores"])
    store.add_embedding(user_id, slot, e["embedding"], json.dumps(e["scores"]["quality"]))
    filled = store.mark_slot_filled(sess["session_id"], slot)
    new_ch = challenge.new_challenge(randomize=sess["randomize"])   # fresh code for the next slot

    # All slots recaptured THIS session -> consistency among the NEW clips only
    # (not against the print being replaced — the whole point of retraining a
    # genuinely changed voice) -> finalize. User stays enrolled=1.
    if len(filled) >= config.ENROLL_SLOTS:
        embs = store.get_embeddings(user_id)
        con = pipeline.enroll_consistency(embs)
        if not con["ok"]:
            store.log_audit(user_id, sess["session_id"], "reenroll", "RETRY", "speaker",
                            json.dumps({"consistency": con}), label)
            return _verdict("RETRY", gate_failed="speaker", reasons=["ENROLL_INCONSISTENT"],
                            scores=auth["scores"], extra={"redo_slot": con["redo_slot"], "consistency": con})
        store.mark_enrolled(user_id)
        store.finish_session(sess["session_id"])
        store.log_audit(user_id, sess["session_id"], "reenroll", "REENROLLED", None,
                        json.dumps({"consistency": con}), label)
        return _verdict("REENROLLED", scores=auth["scores"], extra={"consistency": con})

    store.bump_attempt(sess["session_id"], new_ch)   # rotate the code for the next slot
    store.log_audit(user_id, sess["session_id"], "reenroll", "ENROLL_SLOT_OK", None,
                    json.dumps(auth["scores"]), label)
    return _verdict("ENROLL_SLOT_OK", scores=auth["scores"], new_challenge=new_ch,
                    extra={"slots_done": len(filled), "slots_total": config.ENROLL_SLOTS})


# --- admin ---------------------------------------------------------------- #

def _admin(key: str | None):
    if key != config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/admin/users")
def admin_users(x_admin_key: str | None = Header(None)):
    _admin(x_admin_key)
    return {"users": store.list_users()}


@router.delete("/admin/users/{user_id}")
def admin_delete(user_id: str, x_admin_key: str | None = Header(None)):
    _admin(x_admin_key)
    store.delete_user(user_id)
    return {"deleted": user_id}


@router.post("/admin/users/{user_id}/reset-enrollment")
def admin_reset_enrollment(user_id: str, x_admin_key: str | None = Header(None)):
    """Escape hatch for the case self-service Retrain can't cover: the voice
    changed so much it no longer matches the stored print at all. Wipes the
    voiceprint so the user can go through a fresh /v2/session {mode:"enroll"}. The
    bank must re-verify identity out-of-band (branch/KYC) before calling this —
    the app has no signal that distinguishes a legitimate reset from an attacker."""
    _admin(x_admin_key)
    store.reset_enrollment(user_id)
    return {"reset": user_id}


@router.get("/admin/audit")
def admin_audit(x_admin_key: str | None = Header(None), limit: int = 500):
    _admin(x_admin_key)
    return {"audit": store.dump_audit(limit)}
