"""Voiceprint store + campaign correlation — the fraud-ring intelligence layer.

Each call's wav2vec2 voiceprint is stored; new calls are matched against past
ones. If the *same* synthetic voice hits several customers, those calls cluster
into a campaign; if a voiceprint already committed fraud, the next call from it
is flagged on arrival (blocklist). This is the data network effect competitors
can't replicate.

sqlite + numpy, linear scan. ponytail: linear scan is fine for a demo / a single
branch; swap to FAISS/pgvector only past ~100k stored voiceprints.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid

import numpy as np

_PATH = os.environ.get(
    "DHWANI_VOICEPRINTS_DB",
    os.path.join(os.path.dirname(__file__), "..", "voiceprints.db"),
)
# Cosine-similarity threshold for "same voice". wav2vec2 mean-pooled features,
# not a dedicated speaker space — tune on real data. ponytail: calibrate in PoC.
_SIM = 0.85
_FLAGGED_ACTIONS = {"CHALLENGE", "BLOCK"}

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_PATH, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS calls("
            "call_id TEXT PRIMARY KEY, ts TEXT, cluster_id TEXT, "
            "risk INTEGER, action TEXT, flagged INTEGER, vec BLOB)"
        )
        _conn.commit()
    return _conn


def register(call_id: str, vec: np.ndarray, risk: int, action: str | None) -> dict:
    """Store a voiceprint and correlate it with prior calls. Returns campaign info."""
    vec = vec.astype(np.float32)
    flagged = 1 if action in _FLAGGED_ACTIONS else 0
    with _lock:
        db = _db()
        rows = db.execute("SELECT call_id, cluster_id, flagged, vec FROM calls").fetchall()
        best_sim, best = 0.0, None
        for cid, clid, fl, blob in rows:
            other = np.frombuffer(blob, dtype=np.float32)
            sim = float(np.dot(vec, other))  # both L2-normalised -> cosine
            if sim > best_sim:
                best_sim, best = sim, (cid, clid, fl)

        if best and best_sim >= _SIM:
            cluster_id, match_call, blocklist_hit = best[1], best[0], bool(best[2])
        else:
            cluster_id, match_call, blocklist_hit = uuid.uuid4().hex[:12], None, False

        db.execute(
            "INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?,?,?)",
            (call_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             cluster_id, int(risk), action or "", flagged, vec.tobytes()),
        )
        db.commit()
        size = db.execute("SELECT COUNT(*) FROM calls WHERE cluster_id=?", (cluster_id,)).fetchone()[0]

    return {
        "cluster_id": cluster_id,
        "repeat_voice": match_call is not None,   # seen this voice before
        "match_call_id": match_call,
        "similarity": round(best_sim, 3),
        "cluster_size": size,                      # how many calls this voice hit
        "blocklist_hit": blocklist_hit,            # this voice already committed fraud
    }


def campaigns(min_size: int = 2) -> list[dict]:
    """Voice clusters that hit >= min_size calls — i.e. active campaigns."""
    with _lock:
        db = _db()
        clusters: dict[str, list] = {}
        for cid, clid, ts, risk, action, fl in db.execute(
                "SELECT call_id, cluster_id, ts, risk, action, flagged FROM calls").fetchall():
            clusters.setdefault(clid, []).append(
                {"call_id": cid, "ts": ts, "risk": risk, "action": action, "flagged": fl})
    out = []
    for clid, members in clusters.items():
        if len(members) >= min_size:
            out.append({
                "cluster_id": clid,
                "hits": len(members),
                "flagged_hits": sum(m["flagged"] for m in members),
                "last_seen": max(m["ts"] for m in members),
                "calls": sorted(members, key=lambda m: m["ts"], reverse=True),
            })
    return sorted(out, key=lambda c: c["hits"], reverse=True)


if __name__ == "__main__":
    # ponytail self-check: same voiceprint clusters; an orthogonal one doesn't.
    import tempfile
    _PATH = os.path.join(tempfile.gettempdir(), f"vp_test_{uuid.uuid4().hex}.db")
    _conn = None
    a = np.zeros(768, np.float32); a[0] = 1.0           # voice A
    b = np.zeros(768, np.float32); b[1] = 1.0           # different voice B (orthogonal)
    r1 = register("c1", a, 80, "BLOCK")
    r2 = register("c2", a, 75, "CHALLENGE")             # same voice as c1
    r3 = register("c3", b, 10, "MONITOR")               # different voice
    assert r2["repeat_voice"] and r2["cluster_id"] == r1["cluster_id"], "same voice must cluster"
    assert r2["blocklist_hit"], "c1 was fraud -> c2 should hit the blocklist"
    assert not r3["repeat_voice"], "different voice must not cluster"
    camps = campaigns()
    assert len(camps) == 1 and camps[0]["hits"] == 2, "one 2-call campaign expected"
    print("voiceprints self-check ok")
