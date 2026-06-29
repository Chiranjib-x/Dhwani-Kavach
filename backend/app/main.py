import os

# faster-whisper (ctranslate2) and torch each bundle an Intel OpenMP runtime; on
# Windows both load the same libiomp5md.dll and the duplicate-init check aborts
# the process. They are the same runtime, so allowing the duplicate is safe here.
# Must be set before torch/ctranslate2 import. ponytail: env workaround; the clean
# fix is isolating STT in a subprocess — do that only if numerics ever look off.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes.analyze import router as analyze_router
from app.routes.challenge import router as challenge_router
from app.routes.websocket import router as ws_router

# Production hardening, opt-in via env so local demo stays open:
#   DHWANI_API_KEY   -> if set, /api/* requires header  x-api-key: <key>
#   DHWANI_ORIGINS   -> comma-separated allowed origins (default: * )
_API_KEY = os.environ.get("DHWANI_API_KEY", "")
_ORIGINS = [o.strip() for o in os.environ.get("DHWANI_ORIGINS", "*").split(",") if o.strip()]


async def require_key(x_api_key: str = Header(default="")):
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


app = FastAPI(title="Dhwani-Kavach API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_guard = [Depends(require_key)] if _API_KEY else []
app.include_router(analyze_router, prefix="/api", dependencies=_guard)
app.include_router(challenge_router, prefix="/api", dependencies=_guard)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dhwani-kavach-backend"}
