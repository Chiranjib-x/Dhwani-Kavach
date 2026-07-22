"""FastAPI entrypoint for Dhwani-Kavach v2.

Run from the `backend/` directory (so both `ml` and `verify_app` import as
top-level packages):

    ./.venv/Scripts/python.exe -m uvicorn verify_app.main:app --host 0.0.0.0 --port 8000

Models warm in a background thread at startup; /v2/health reports readiness.
"""
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from verify_app import models

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm models off the event loop so the server accepts connections (and can
    # answer /v2/health with models_loaded:false) while they load.
    threading.Thread(target=models.load_all, name="warm-models", daemon=True).start()
    yield


app = FastAPI(title="Dhwani-Kavach v2 — Voice Verify", lifespan=lifespan)

# Open CORS: the React dev server (5173) and any demo device call this API
# cross-origin. Fine for a hackathon demo; tighten to the deployed origin later.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def _security_headers(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/v2"):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/v2/health")
def health():
    return JSONResponse({"status": "ok", "models_loaded": models.ready(), **models.status()})


from verify_app.api import router as v2_router  # noqa: E402
app.include_router(v2_router)

# Static capture page (Phase 1). Mounted last so /v2/* wins. Created lazily so a
# fresh checkout without the static dir still boots.
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
