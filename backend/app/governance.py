"""Model governance — the procurement unlock (banks must govern what they deploy).

Analysts label flagged calls (fraud/legit); we join those labels against the
audit log to compute a live confusion matrix (TPR / FPR / precision), watch for
verdict drift over time, and expose the model registry (version, training data,
eval scores, champion/challenger). RBI Model Risk Management in miniature.

sqlite labels + the JSONL audit log + a JSON registry. ponytail: simple counts
and a two-window drift heuristic; add proper time-series/PSI in a PoC.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

from app import audit

_LABELS_DB = os.environ.get("DHWANI_LABELS_DB",
                            os.path.join(os.path.dirname(__file__), "..", "labels.db"))
_REGISTRY = os.environ.get("DHWANI_MODEL_REGISTRY",
                           os.path.join(os.path.dirname(__file__), "..", "model_registry.json"))
_FLAGGED_LEVELS = {"RED", "AMBER"}
_FLAGGED_ACTIONS = {"CHALLENGE", "BLOCK"}
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_LABELS_DB, check_same_thread=False)
        _conn.execute("CREATE TABLE IF NOT EXISTS labels(call_id TEXT PRIMARY KEY, label TEXT, ts TEXT)")
        _conn.commit()
    return _conn


def label_case(call_id: str, label: str) -> str:
    """Record an analyst label. Anything starting with 'f' -> fraud, else legit."""
    norm = "fraud" if str(label).lower().startswith("f") else "legit"
    with _lock:
        _db().execute("INSERT OR REPLACE INTO labels VALUES (?,?,?)",
                      (call_id, norm, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        _db().commit()
    return norm


def _labels() -> dict:
    with _lock:
        return dict(_db().execute("SELECT call_id, label FROM labels").fetchall())


def _audit_rows() -> list[dict]:
    try:
        with open(audit._PATH, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


def _flagged(r: dict) -> bool:
    return r.get("alert_level") in _FLAGGED_LEVELS or r.get("action") in _FLAGGED_ACTIONS


def _rate(a: int, b: int):
    return round(a / (a + b), 3) if (a + b) else None


def confusion() -> dict:
    """Confusion matrix from labelled calls joined to their audit verdict."""
    labels = _labels()
    idx = {r.get("call_id"): r for r in _audit_rows() if r.get("call_id")}
    tp = fp = tn = fn = 0
    for cid, lab in labels.items():
        a = idx.get(cid)
        if not a:
            continue
        pred, actual = _flagged(a), (lab == "fraud")
        if pred and actual: tp += 1
        elif pred and not actual: fp += 1
        elif not pred and actual: fn += 1
        else: tn += 1
    return {"labeled": tp + fp + tn + fn, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "tpr": _rate(tp, fn), "fpr": _rate(fp, tn), "precision": _rate(tp, fp)}


def drift(recent: int = 20) -> dict:
    """Compare the flagged-rate in the recent window vs the earlier baseline."""
    flags = [1 if _flagged(r) else 0 for r in _audit_rows() if r.get("alert_level")]
    if len(flags) < 4:
        return {"enough_data": False}
    base = flags[:-recent] or flags[: len(flags) // 2]
    rec = flags[-recent:]
    br, rr = sum(base) / len(base), sum(rec) / len(rec)
    d = round(rr - br, 3)
    return {"enough_data": True, "baseline_flag_rate": round(br, 3),
            "recent_flag_rate": round(rr, 3), "drift": d, "alert": abs(d) >= 0.2, "n": len(flags)}


def registry() -> dict:
    try:
        with open(_REGISTRY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"models": []}


if __name__ == "__main__":
    import tempfile, uuid
    _LABELS_DB = os.path.join(tempfile.gettempdir(), f"lbl_{uuid.uuid4().hex}.db"); _conn = None
    audit._PATH = os.path.join(tempfile.gettempdir(), f"aud_{uuid.uuid4().hex}.jsonl")
    with open(audit._PATH, "w") as f:
        f.write(json.dumps({"call_id": "a", "alert_level": "RED", "action": "BLOCK"}) + "\n")
        f.write(json.dumps({"call_id": "b", "alert_level": "GREEN", "action": "MONITOR"}) + "\n")
    assert label_case("a", "fraud") == "fraud" and label_case("b", "legit") == "legit"
    c = confusion()
    assert c["tp"] == 1 and c["tn"] == 1 and c["fp"] == 0 and c["fn"] == 0, c
    assert c["tpr"] == 1.0 and c["fpr"] == 0.0, c
    print("governance self-check ok")
