"""Lazy model loading + readiness reporting.

`load_all()` warms every heavy model once (ECAPA, faster-whisper, the CM) so the
first real request isn't slow. It runs in a background thread at startup; until
it finishes, `/v2/health` reports models_loaded:false and the frontend shows a
"waking up" state (free-tier cold start can take tens of seconds).

Phases 3/4/5 fill in the actual loaders. Phase 0 ships the scaffold: nothing is
loaded yet, so ready() is False.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_state = {"speaker": False, "asr": False, "liveness": False, "error": None}


def ready() -> bool:
    """True once every heavy model is loaded and the pipeline can serve verdicts."""
    with _lock:
        return all(_state[k] for k in ("speaker", "asr", "liveness"))


def status() -> dict:
    with _lock:
        return dict(_state)


def _mark(name: str, ok: bool) -> None:
    with _lock:
        _state[name] = ok


def load_all() -> None:
    """Warm every model. Idempotent; safe to call from a background thread.

    Each loader is filled in by its phase:
      speaker  -> verify_app.speaker.load()      (Phase 3)
      asr      -> verify_app.asr.load()          (Phase 4)
      liveness -> verify_app.liveness.load()     (Phase 5)
    A loader failing marks only its own component un-ready and records the error;
    it never crashes the server (a bank deployment must still boot to report health).
    """
    loaders = [
        ("speaker", "verify_app.speaker", "load"),
        ("asr", "verify_app.asr", "load"),
        ("liveness", "verify_app.liveness", "load"),
    ]
    for name, module, fn in loaders:
        try:
            mod = __import__(module, fromlist=[fn])
            getattr(mod, fn)()
            _mark(name, True)
        except Exception as e:  # noqa: BLE001 — health must survive any loader failure
            _mark(name, False)
            with _lock:
                _state["error"] = f"{name}: {type(e).__name__}: {e}"
