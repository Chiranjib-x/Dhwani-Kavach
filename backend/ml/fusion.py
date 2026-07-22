"""Decision fusion — turn raw scores into an action a fraud engine can take.

Banks act on decisions, not scores. This combines the deepfake risk, the
scam-script risk, the novelty (zero-day) flag and the transaction context into
one of MONITOR / CHALLENGE / BLOCK, with a one-line human-readable reason.

Rule-based on purpose: every decision must be explainable to an auditor.
ponytail: rules, not ML — swap for a learned policy only if a bank PoC shows rules miss cases.
"""
from __future__ import annotations

from ml.scoring import thresholds as _score_thresholds

# A new payee or a large transfer turns a "suspicious voice" into "stop the money".
_HIGH_VALUE = 50_000  # ₹; tune to the bank's risk appetite


def _escalation(action: str, coercion: bool) -> dict:
    """What the flagged call should escalate INTO — this is what makes the shield
    a funnel, not a dead end. A verdict of CHALLENGE/BLOCK hands off to the voice
    step-up (the verify app: dynamic spoken-digit code + 1:1 voiceprint), EXCEPT
    when the driver is coercion/APP-fraud: a genuine but coached customer passes
    every voice check, so a second voice gate is theatre — route them to a human."""
    if action == "MONITOR":
        return {"required": False, "method": None, "reason": ""}
    if coercion:
        return {"required": True, "method": "human_review",
                "reason": "possible coerced customer — voice auth can't clear this; "
                          "route to a human agent + cooling-off before the money moves"}
    return {"required": True, "method": "voice_otp",
            "reason": "step up with a live spoken-digit voice-OTP (fresh code + 1:1 "
                      "voiceprint) — a recording or loudspeaker replay can't complete it"}


def fuse(
    deepfake_risk: int,
    scam_score: int = 0,
    novelty: float = 0.0,
    txn: dict | None = None,
    quality_ok: bool = True,
    quality_reason: str = "",
    replay_suspect: bool = False,
) -> dict:
    """
    Parameters
    ----------
    deepfake_risk : 0-100 from the audio ensemble.
    scam_score    : 0-100 from the scam-script layer (0 if unavailable).
    novelty       : 0-1, "unknown synthesis signature" likelihood.
    txn           : optional {amount: float, new_beneficiary: bool}.
    quality_ok    : False when input quality was too low to trust the voice score.
    quality_reason: human-readable quality failure (shown to the agent).
    replay_suspect: True when ml.replay flags a loudspeaker-replay channel
                    signature (see ml/replay.py). The neural detector was not
                    trained on this channel and can read falsely clean on it --
                    a clean voice score over a suspected replay is exactly the
                    "clone played from a phone speaker" bypass, so it must not
                    clear to MONITOR on the voice score alone.

    Returns {action, action_reason}.
    """
    txn = txn or {}
    coercion = scam_score >= 70
    # When the input is too degraded to judge the voice, we CANNOT clear the call
    # (a laundered deepfake reads unreliable, not clean) and we must NOT block on a
    # score we don't trust. The honest action is to step up authentication.
    if not quality_ok:
        reason = quality_reason or "input quality too low to assess the voice"
        return {"action": "CHALLENGE",
                "action_reason": f"{reason} — verify the caller another way",
                "novelty": novelty,
                "escalation": _escalation("CHALLENGE", coercion)}
    high_value = bool(txn.get("new_beneficiary")) or float(txn.get("amount", 0) or 0) >= _HIGH_VALUE

    # deepfake_risk's RED threshold must match ml.detector's alert_level banding --
    # otherwise a RED badge with a MONITOR action (or vice versa) reads as broken.
    _, voice_red_threshold = _score_thresholds()
    voice_red = deepfake_risk >= voice_red_threshold
    scam_red = coercion
    novel = novelty >= 0.6

    reasons = []
    if voice_red:
        reasons.append(f"synthetic-voice risk {deepfake_risk}")
    if scam_red:
        reasons.append(f"APP-fraud/coercion risk {scam_score}")

    threat = voice_red or scam_red

    if threat and high_value:
        action = "BLOCK"
        ctx = "new payee" if txn.get("new_beneficiary") else f"₹{int(txn.get('amount', 0)):,} transfer"
        reason = f"{' + '.join(reasons)} during a {ctx}"
    elif threat:
        action = "CHALLENGE"
        reason = f"{' + '.join(reasons)} — step up authentication"
    else:
        action = "MONITOR"
        reason = "no fraud signal above threshold"

    if novel:
        reason += " (elevated novelty noted)"

    # Replay-channel gate (last word, like the quality gate above): a suspected
    # loudspeaker replay can't be waved through as MONITOR just because the
    # voice score read clean -- that score isn't trustworthy on this channel.
    # Doesn't escalate an already-BLOCK/CHALLENGE decision's severity, just
    # documents the extra evidence and prevents a silent false-clear.
    if replay_suspect:
        if action == "MONITOR":
            action = "CHALLENGE"
            reason = "loudspeaker replay suspected — voice channel can't be trusted, verify another way"
        else:
            reason += " (loudspeaker replay suspected)"

    return {"action": action, "action_reason": reason, "novelty": novelty,
            "escalation": _escalation(action, scam_red)}


if __name__ == "__main__":
    # Self-check the escalation routing — the integration's load-bearing branch:
    # a clean call doesn't escalate; a synthetic/replay flag routes to voice-OTP;
    # a coercion flag routes to a human (a coached real customer beats voice auth).
    clean = fuse(deepfake_risk=5, scam_score=0)
    assert clean["action"] == "MONITOR" and not clean["escalation"]["required"]

    synthetic = fuse(deepfake_risk=95, scam_score=0)
    assert synthetic["action"] == "CHALLENGE"
    assert synthetic["escalation"]["method"] == "voice_otp"

    coerced = fuse(deepfake_risk=5, scam_score=90, txn={"new_beneficiary": True})
    assert coerced["action"] == "BLOCK"  # coercion + new payee
    assert coerced["escalation"]["method"] == "human_review"

    replayed = fuse(deepfake_risk=5, scam_score=0, replay_suspect=True)
    assert replayed["action"] == "CHALLENGE"  # replay gate forces step-up
    assert replayed["escalation"]["method"] == "voice_otp"
    print("fusion escalation self-check ok")
