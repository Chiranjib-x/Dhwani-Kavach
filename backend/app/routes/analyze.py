import asyncio
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from ml.audio_utils import load_audio_bytes
from ml.detector import detect_samples
from ml import scam_detector
from ml.fusion import fuse
from app import audit, metrics

router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # ponytail: 25 MB cap; raise if real calls run longer


class AnalysisResult(BaseModel):
    risk_score: int
    alert_level: str
    layer_breakdown: dict
    novelty: float = 0.0
    scam: dict = {}
    action: str = "MONITOR"
    action_reason: str = ""


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_audio(
    audio: UploadFile = File(...),
    amount: float = Form(0),
    new_beneficiary: bool = Form(False),
):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty audio upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB).")
    t0 = time.monotonic()
    try:
        samples, _ = await asyncio.to_thread(load_audio_bytes, data)
        # CPU-bound torch inference + (optional) STT/LLM — keep off the event loop.
        result = await asyncio.to_thread(detect_samples, samples)
        scam = await asyncio.to_thread(scam_detector.analyze, samples)
    except Exception as exc:
        metrics.record_error("rest")
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result["scam"] = scam
    result.update(fuse(
        deepfake_risk=result["risk_score"],
        scam_score=scam.get("score", 0),
        novelty=result.get("novelty", 0.0),
        txn={"amount": amount, "new_beneficiary": new_beneficiary},
    ))
    audit.record("rest", result)
    metrics.observe_latency(time.monotonic() - t0)
    metrics.record_verdict("rest", result["alert_level"], result.get("action"))
    return AnalysisResult(**result)
