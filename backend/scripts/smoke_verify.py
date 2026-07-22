"""Phase 6 smoke test (MASTER-PLAN §8) — the full cascade + session state machine
over the real API, with real liveness+speaker models on genuine audio.

ASR is a controlled seam: `_SPOKEN` = what the current recording actually says.
For a genuine caller it equals the issued challenge; for a replay it stays the
OLD digits while a new challenge was issued (exactly what a replayed file does).
This models the recording's spoken content honestly — the one variable static
fixtures can't carry — while Gates 0/2/3 run for real. ASR accuracy itself is
covered by verify_app/selfcheck_challenge.py.

Run from backend/:  ../.venv/Scripts/python.exe scripts/smoke_verify.py
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

from fastapi.testclient import TestClient  # noqa: E402

from verify_app import asr, config, store  # noqa: E402

_SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "sample_audio")
SR = 16000

_SPOKEN = {"text": ""}                      # what the "recording" says right now
asr.transcribe = lambda wav: _SPOKEN["text"]  # controlled ASR seam


def _wav_bytes(wav: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, wav, SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _load(name: str) -> np.ndarray:
    import librosa
    wav, _ = librosa.load(os.path.join(_SAMPLES, name), sr=SR, mono=True)
    return wav.astype(np.float32)


def _post_audio(client, session_id, wav, slot=0):
    return client.post("/v2/audio", data={"session_id": session_id, "slot": str(slot)},
                       files={"file": ("clip.wav", _wav_bytes(wav), "audio/wav")}).json()


def main() -> None:
    config.__dict__["DB_PATH"] = os.path.join(os.environ.get("TEMP", "/tmp"), "kv_smoke.db")
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    store._conn = None

    from verify_app.main import app
    client = TestClient(app)

    chris = _load("chris_original.mp3")
    lily = _load("lily_original.mp3")[: 8 * SR]      # keep within DUR_MAX
    n = len(chris) // 5
    slices = [chris[i * n:(i + 1) * n] for i in range(5)]   # 5 slices of the same speaker

    # 1) enroll chris with 3 slices -> ENROLLED
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "enroll"}).json()
    sid = s["session_id"]
    v0 = _post_audio(client, sid, slices[0], 0)
    v1 = _post_audio(client, sid, slices[1], 1)
    v2 = _post_audio(client, sid, slices[2], 2)
    print("enroll:", v0["verdict"], v1["verdict"], v2["verdict"])
    assert v2["verdict"] == "ENROLLED", v2

    # 2) genuine verify (says the challenge) -> ACCEPT
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "verify"}).json()
    _SPOKEN["text"] = s["challenge"]
    v = _post_audio(client, s["session_id"], slices[3])
    print("genuine verify:", v["verdict"], "speaker", v["scores"]["speaker"])
    assert v["verdict"] == "ACCEPT", v

    # 3) replay: new session (new challenge) but recording still says the OLD digits
    old_challenge = s["challenge"]
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "verify"}).json()
    assert s["challenge"] != old_challenge, "challenge must be fresh per session"
    _SPOKEN["text"] = old_challenge                     # replayed file carries old digits
    v = _post_audio(client, s["session_id"], slices[3])
    print("replay:", v["verdict"], v["reasons"])
    assert v["verdict"] == "RETRY" and "WRONG_PHRASE" in v["reasons"], v

    # 4) impostor: right digits, wrong voice -> REJECT VOICE_MISMATCH
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "verify"}).json()
    _SPOKEN["text"] = s["challenge"]
    v = _post_audio(client, s["session_id"], lily)
    print("impostor:", v["verdict"], v["reasons"], "speaker", v["scores"]["speaker"])
    assert v["verdict"] == "REJECT" and "VOICE_MISMATCH" in v["reasons"], v

    # 5) expired session -> SESSION_EXPIRED
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "verify"}).json()
    store._db().execute("UPDATE sessions SET expires_at=0 WHERE session_id=?", (s["session_id"],))
    store._db().commit()
    _SPOKEN["text"] = s["challenge"]
    v = _post_audio(client, s["session_id"], slices[3])
    print("expired:", v["verdict"], v["reasons"])
    assert "SESSION_EXPIRED" in v["reasons"], v

    # 6) admin key gate
    assert client.get("/v2/admin/users", headers={"X-Admin-Key": "wrong"}).status_code == 403
    ok = client.get("/v2/admin/users", headers={"X-Admin-Key": config.ADMIN_KEY})
    assert ok.status_code == 200 and any(u["user_id"] == "chris" for u in ok.json()["users"])
    print("admin: 403 on wrong key, 200 on right key")

    print("\nsmoke_verify: all 6 checks passed [OK]")


if __name__ == "__main__":
    main()
