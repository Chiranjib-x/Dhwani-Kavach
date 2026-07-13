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


def fuse(
    deepfake_risk: int,
    scam_score: int = 0,
    novelty: float = 0.0,
    txn: dict | None = None,
) -> dict:
    """
    Parameters
    ----------
    deepfake_risk : 0-100 from the audio ensemble.
    scam_score    : 0-100 from the scam-script layer (0 if unavailable).
    novelty       : 0-1, "unknown synthesis signature" likelihood.
    txn           : optional {amount: float, new_beneficiary: bool}.

    Returns {action, action_reason}.
    """
    txn = txn or {}
    high_value = bool(txn.get("new_beneficiary")) or float(txn.get("amount", 0) or 0) >= _HIGH_VALUE

    # deepfake_risk's RED threshold must match ml.detector's alert_level banding --
    # otherwise a RED badge with a MONITOR action (or vice versa) reads as broken.
    _, voice_red_threshold = _score_thresholds()
    voice_red = deepfake_risk >= voice_red_threshold
    scam_red = scam_score >= 70
    novel = novelty >= 0.6

    reasons = []
    if voice_red:
        reasons.append(f"synthetic-voice risk {deepfake_risk}")
    if scam_red:
        reasons.append(f"scam-script risk {scam_score}")

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

    return {"action": action, "action_reason": reason, "novelty": novelty}
