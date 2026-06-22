import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from ml.detector import detect_audio

router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # ponytail: 25 MB cap; raise if real calls run longer


class AnalysisResult(BaseModel):
    risk_score: int
    alert_level: str
    layer_breakdown: dict


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_audio(audio: UploadFile = File(...)):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty audio upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB).")
    try:
        # CPU-bound torch inference — keep it off the event loop.
        result = await asyncio.to_thread(detect_audio, data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AnalysisResult(**result)
