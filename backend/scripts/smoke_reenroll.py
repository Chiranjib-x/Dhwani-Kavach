"""Smoke test for re-enrollment ("retrain an existing user's voiceprint").

Retrain is authorized BY the voice now (device binding removed): every new clip
must pass a full verification (quality + phrase + liveness + speaker match)
against the CURRENT voiceprint before it is captured.

Proves: (1) the enrolled customer, reading the live one-time code, CAN retrain
and the stored embeddings actually change; (2) a DIFFERENT speaker (even reading
the correct code) can't — refused, nothing stored; (3) the right speaker reading
the WRONG code can't — refused, nothing stored; (4) the admin reset-enrollment
escape hatch wipes the voiceprint so a fresh enroll works afterward.

ASR is the same controlled seam as smoke_verify (we model the spoken digits);
the liveness+speaker models run for real on genuine audio.

Run from backend/:  ../.venv/Scripts/python.exe scripts/smoke_reenroll.py
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
_SPOKEN = {"text": ""}
asr.transcribe = lambda wav: _SPOKEN["text"]   # model the digits the caller read


def _wav_bytes(wav):
    buf = io.BytesIO(); sf.write(buf, wav, SR, format="WAV", subtype="PCM_16"); return buf.getvalue()


def _load(name):
    import librosa
    wav, _ = librosa.load(os.path.join(_SAMPLES, name), sr=SR, mono=True)
    return wav.astype(np.float32)


def _post(client, sid, wav, slot):
    return client.post("/v2/audio", data={"session_id": sid, "slot": str(slot)},
                       files={"file": ("c.wav", _wav_bytes(wav), "audio/wav")}).json()


def _slices(wav, n=5):
    step = len(wav) // n
    return [wav[i * step:(i + 1) * step] for i in range(n)]


def main():
    config.__dict__["DB_PATH"] = os.path.join(os.environ.get("TEMP", "/tmp"), "kv_reenroll.db")
    for suffix in ("", "-wal", "-shm"):
        try: os.remove(config.DB_PATH + suffix)
        except OSError: pass
    store._conn = None

    from verify_app.main import app
    client = TestClient(app)

    chris = _slices(_load("chris_original.mp3"))
    lily = _slices(_load("lily_original.mp3"))          # a DIFFERENT genuine speaker

    # enroll chris (slots 0,1,2)
    s = client.post("/v2/session", json={"user_id": "chris", "mode": "enroll"}).json()
    for i in range(3):
        _post(client, s["session_id"], chris[i], slot=i)
    original = [v.copy() for v in store.get_embeddings("chris")]
    assert len(original) == 3, f"expected 3 enroll embeddings, got {len(original)}"
    print(f"enrolled; {len(original)} embeddings stored")

    unchanged = lambda: all(np.array_equal(a, b) for a, b in zip(store.get_embeddings("chris"), original))

    # 1) WRONG SPEAKER, correct code -> refused, nothing stored
    r = client.post("/v2/session", json={"user_id": "chris", "mode": "reenroll"}).json()
    _SPOKEN["text"] = r["challenge"]
    v = _post(client, r["session_id"], lily[3], slot=0)
    print("reenroll, wrong speaker:", v["verdict"], v["reasons"])
    assert v["verdict"] == "RETRY", v            # speaker gate refuses; capture nothing
    assert unchanged(), "a different speaker must NOT change the voiceprint"

    # 2) RIGHT SPEAKER, wrong code -> refused, nothing stored
    r = client.post("/v2/session", json={"user_id": "chris", "mode": "reenroll"}).json()
    _SPOKEN["text"] = "000000" if r["challenge"] != "000000" else "111111"
    v = _post(client, r["session_id"], chris[3], slot=0)
    print("reenroll, wrong code   :", v["verdict"], v["reasons"])
    assert v["verdict"] == "RETRY" and "WRONG_PHRASE" in v["reasons"], v
    assert unchanged(), "reading the wrong code must NOT change the voiceprint"

    # 3) AUTHORIZED: chris reads the live code for all 3 slots -> REENROLLED, embeddings change.
    #    New clips {1,2,3} differ from the enrolled set {0,1,2}, so a change proves
    #    a real overwrite, not a no-op re-save.
    r = client.post("/v2/session", json={"user_id": "chris", "mode": "reenroll"}).json()
    ch = r["challenge"]
    for i, clip in enumerate((chris[1], chris[2], chris[3])):
        _SPOKEN["text"] = ch
        v = _post(client, r["session_id"], clip, slot=i)
        print(f"reenroll slot {i}:", v["verdict"])
        assert v["verdict"] in ("ENROLL_SLOT_OK", "REENROLLED"), v
        ch = v.get("new_challenge", ch)
    assert v["verdict"] == "REENROLLED", v
    changed = any(not np.array_equal(a, b) for a, b in zip(store.get_embeddings("chris"), original))
    print("embeddings changed after retrain:", changed)
    assert changed, "retrain should overwrite the stored voiceprint"
    assert store.get_user("chris")["enrolled"], "user must remain enrolled after retrain"

    # 4) admin reset-enrollment: wipes the voiceprint, fresh enroll works
    a = client.post("/v2/admin/users/chris/reset-enrollment", headers={"X-Admin-Key": config.ADMIN_KEY}).json()
    assert a.get("reset") == "chris", a
    assert store.get_embeddings("chris") == [], "embeddings must be wiped"
    assert not store.get_user("chris")["enrolled"], "user must be un-enrolled"
    fresh = client.post("/v2/session", json={"user_id": "chris", "mode": "enroll"}).json()
    assert "session_id" in fresh, f"fresh enroll should be allowed: {fresh}"
    print("admin reset-enrollment: wiped + fresh enroll allowed")

    print("\nsmoke_reenroll: all checks passed [OK]")


if __name__ == "__main__":
    main()
