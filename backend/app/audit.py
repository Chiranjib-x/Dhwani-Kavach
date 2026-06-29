"""Append-only verdict audit log — compliance trail + forensic evidence, no audio.

One JSON line per verdict with a stable call_id, so a flagged call can be pulled
up as an evidence pack (transcript, tactics, layers that fired, decision). Audio
is never written; the transcript is text only.
ponytail: single JSONL append; move to the bank's SIEM/DB at integration time.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

_PATH = os.environ.get(
    "DHWANI_AUDIT_LOG",
    os.path.join(os.path.dirname(__file__), "..", "audit_log.jsonl"),
)
_lock = threading.Lock()


def record(source: str, result: dict) -> str:
    """Append a verdict and return its call_id. Never raises into the request path."""
    call_id = result.get("call_id") or uuid.uuid4().hex[:12]
    scam = result.get("scam", {}) or {}
    entry = {
        "call_id": call_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "risk_score": result.get("risk_score"),
        "alert_level": result.get("alert_level"),
        "novelty": result.get("novelty"),
        "scam_score": scam.get("score"),
        "tactics": scam.get("tactics", []),
        "language": scam.get("language", ""),
        "transcript": scam.get("transcript", ""),
        "layer_breakdown": result.get("layer_breakdown", {}),
        "action": result.get("action"),
        "action_reason": result.get("action_reason", ""),
        "mode": result.get("mode"),
        "enforced": result.get("enforced"),
    }
    try:
        with _lock, open(_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # auditing must never break detection
    return call_id
