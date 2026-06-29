"""Append-only verdict audit log — compliance trail, no audio stored.

One JSON line per verdict: timestamp, source, scores, action. This is the
artifact a bank's audit/compliance team asks for. Audio is never written.
ponytail: single JSONL append; move to the bank's SIEM/DB at integration time.
"""
from __future__ import annotations

import json
import os
import threading
import time

_PATH = os.environ.get(
    "DHWANI_AUDIT_LOG",
    os.path.join(os.path.dirname(__file__), "..", "audit_log.jsonl"),
)
_lock = threading.Lock()


def record(source: str, result: dict) -> None:
    """Append a verdict. Never raises into the request path."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "risk_score": result.get("risk_score"),
        "alert_level": result.get("alert_level"),
        "scam_score": result.get("scam", {}).get("score"),
        "novelty": result.get("novelty"),
        "action": result.get("action"),
    }
    try:
        line = json.dumps(entry)
        with _lock, open(_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # auditing must never break detection
