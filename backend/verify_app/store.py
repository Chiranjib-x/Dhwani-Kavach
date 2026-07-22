"""sqlite persistence: users, enrollment embeddings, sessions, audit, lockouts.

One module-level connection guarded by a lock (the pattern from app/voiceprints.py,
which is already correct). WAL mode so a reader never blocks the single writer —
and so OneDrive's file locking is less likely to corrupt the dev DB (see
MASTER-PLAN §11; set KAVACH_DB to a temp path if it still misbehaves).

Embeddings are stored as raw float32 bytes and are NOT invertible to speech.
Raw audio is never stored here.
"""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid

import numpy as np

from verify_app import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  user_id TEXT PRIMARY KEY, display_name TEXT,
  enrolled INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS embeddings(
  user_id TEXT, slot INTEGER, vec BLOB, quality_json TEXT, created_at TEXT,
  PRIMARY KEY(user_id, slot));
CREATE TABLE IF NOT EXISTS sessions(
  session_id TEXT PRIMARY KEY, user_id TEXT, mode TEXT,
  challenge TEXT, expires_at REAL, attempts INTEGER DEFAULT 0, done INTEGER DEFAULT 0,
  randomize INTEGER DEFAULT 1, filled_slots TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user_id TEXT, session_id TEXT,
  mode TEXT, verdict TEXT, gate_failed TEXT, scores_json TEXT, label TEXT);
CREATE TABLE IF NOT EXISTS lockouts(
  user_id TEXT PRIMARY KEY, fails INTEGER, until REAL);
"""


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
        _migrate(_conn)
        _conn.commit()
    return _conn


# Columns added after a DB may already exist. CREATE TABLE IF NOT EXISTS never
# alters an existing table, so a pre-existing kavach.db keeps its old schema and
# breaks on the new INSERT. Add missing columns idempotently instead of forcing a
# manual delete on every schema change.
_MIGRATIONS = [("sessions", "randomize", "INTEGER DEFAULT 1"),
               ("sessions", "filled_slots", "TEXT DEFAULT ''")]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, col, decl in _MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- users ---------------------------------------------------------------- #

def create_user(user_id: str, display_name: str | None = None) -> None:
    with _lock:
        _db().execute(
            "INSERT OR IGNORE INTO users(user_id, display_name, enrolled, created_at) VALUES(?,?,0,?)",
            (user_id, display_name or user_id, _now()))
        _db().commit()


def get_user(user_id: str) -> dict | None:
    with _lock:
        r = _db().execute(
            "SELECT user_id, display_name, enrolled FROM users WHERE user_id=?", (user_id,)).fetchone()
    return {"user_id": r[0], "display_name": r[1], "enrolled": bool(r[2])} if r else None


def mark_enrolled(user_id: str) -> None:
    with _lock:
        _db().execute("UPDATE users SET enrolled=1 WHERE user_id=?", (user_id,))
        _db().commit()


def list_users() -> list[dict]:
    with _lock:
        rows = _db().execute(
            "SELECT user_id, display_name, enrolled, created_at FROM users ORDER BY created_at").fetchall()
    return [{"user_id": r[0], "display_name": r[1], "enrolled": bool(r[2]), "created_at": r[3]} for r in rows]


def delete_user(user_id: str) -> None:
    """GDPR/DPDP delete: wipe the user and every trace of their biometric data."""
    with _lock:
        db = _db()
        for tbl in ("embeddings", "sessions", "lockouts"):
            db.execute(f"DELETE FROM {tbl} WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        db.commit()


def reset_enrollment(user_id: str) -> None:
    """Admin escape hatch: wipe a user's voiceprint so they can fully re-enroll
    from scratch — the case self-service Retrain can't cover (the voice changed
    so much it no longer matches the stored print). The bank must re-verify
    identity out-of-band (branch/KYC) before calling this; the app has no way to
    know a reset request is legitimate."""
    with _lock:
        db = _db()
        db.execute("DELETE FROM embeddings WHERE user_id=?", (user_id,))
        db.execute("UPDATE users SET enrolled=0 WHERE user_id=?", (user_id,))
        db.commit()


# --- embeddings ----------------------------------------------------------- #

def add_embedding(user_id: str, slot: int, vec: np.ndarray, quality_json: str) -> None:
    with _lock:
        _db().execute(
            "INSERT OR REPLACE INTO embeddings(user_id, slot, vec, quality_json, created_at) VALUES(?,?,?,?,?)",
            (user_id, int(slot), vec.astype(np.float32).tobytes(), quality_json, _now()))
        _db().commit()


def get_embeddings(user_id: str) -> list[np.ndarray]:
    with _lock:
        rows = _db().execute(
            "SELECT vec FROM embeddings WHERE user_id=? ORDER BY slot", (user_id,)).fetchall()
    return [np.frombuffer(r[0], dtype=np.float32) for r in rows]


# --- sessions ------------------------------------------------------------- #

def create_session(user_id: str, mode: str, challenge: str | None,
                   randomize: bool = True) -> dict:
    sid = uuid.uuid4().hex
    expires = time.time() + config.SESSION_TTL_S
    with _lock:
        _db().execute(
            "INSERT INTO sessions(session_id, user_id, mode, challenge, expires_at, attempts, done, randomize) "
            "VALUES(?,?,?,?,?,0,0,?)", (sid, user_id, mode, challenge, expires, 1 if randomize else 0))
        _db().commit()
    return {"session_id": sid, "user_id": user_id, "mode": mode, "challenge": challenge,
            "expires_at": expires, "randomize": randomize}


def get_session(session_id: str) -> dict | None:
    with _lock:
        r = _db().execute(
            "SELECT session_id, user_id, mode, challenge, expires_at, attempts, done, randomize, filled_slots "
            "FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    if not r:
        return None
    return {"session_id": r[0], "user_id": r[1], "mode": r[2], "challenge": r[3],
            "expires_at": r[4], "attempts": r[5], "done": bool(r[6]), "randomize": bool(r[7]),
            "filled_slots": {int(s) for s in r[8].split(",") if s}}


def mark_slot_filled(session_id: str, slot: int) -> set[int]:
    """Record that `slot` was successfully (re)recorded IN THIS SESSION, and
    return the updated set. Enrollment/re-enrollment completion is judged by this
    — not by counting a user's total stored embeddings — because on a RE-enroll
    the user already has old rows for every slot; counting the table would treat
    the session as 'done' after the first overwritten slot, using two stale old
    embeddings for the consistency check instead of waiting for all 3 new ones."""
    with _lock:
        db = _db()
        cur = db.execute("SELECT filled_slots FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        filled = {int(s) for s in (cur[0] or "").split(",") if s} if cur else set()
        filled.add(int(slot))
        db.execute("UPDATE sessions SET filled_slots=? WHERE session_id=?",
                   (",".join(str(s) for s in sorted(filled)), session_id))
        db.commit()
    return filled


def bump_attempt(session_id: str, new_challenge: str | None = None) -> None:
    with _lock:
        if new_challenge is not None:
            _db().execute("UPDATE sessions SET attempts=attempts+1, challenge=? WHERE session_id=?",
                          (new_challenge, session_id))
        else:
            _db().execute("UPDATE sessions SET attempts=attempts+1 WHERE session_id=?", (session_id,))
        _db().commit()


def finish_session(session_id: str) -> None:
    with _lock:
        _db().execute("UPDATE sessions SET done=1 WHERE session_id=?", (session_id,))
        _db().commit()


# --- lockouts ------------------------------------------------------------- #

def check_lockout(user_id: str) -> bool:
    """True if the user is currently locked out."""
    with _lock:
        r = _db().execute("SELECT until FROM lockouts WHERE user_id=?", (user_id,)).fetchone()
    return bool(r) and r[0] > time.time()


def record_fail(user_id: str) -> None:
    """Count a failed verify session; arm a lockout once it crosses the threshold."""
    with _lock:
        db = _db()
        r = db.execute("SELECT fails, until FROM lockouts WHERE user_id=?", (user_id,)).fetchone()
        fails = (r[0] if r else 0) + 1
        until = time.time() + config.LOCKOUT_MIN * 60 if fails >= config.LOCKOUT_FAILS else 0.0
        db.execute("INSERT OR REPLACE INTO lockouts(user_id, fails, until) VALUES(?,?,?)",
                   (user_id, fails, until))
        db.commit()


def clear_fails(user_id: str) -> None:
    with _lock:
        _db().execute("DELETE FROM lockouts WHERE user_id=?", (user_id,))
        _db().commit()


# --- audit ---------------------------------------------------------------- #

def log_audit(user_id: str, session_id: str, mode: str, verdict: str,
              gate_failed: str | None, scores_json: str, label: str | None = None) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO audit(ts, user_id, session_id, mode, verdict, gate_failed, scores_json, label) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (_now(), user_id, session_id, mode, verdict, gate_failed, scores_json, label))
        _db().commit()


def dump_audit(limit: int = 500) -> list[dict]:
    with _lock:
        rows = _db().execute(
            "SELECT ts, user_id, session_id, mode, verdict, gate_failed, scores_json, label "
            "FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    keys = ("ts", "user_id", "session_id", "mode", "verdict", "gate_failed", "scores_json", "label")
    return [dict(zip(keys, r)) for r in rows]
