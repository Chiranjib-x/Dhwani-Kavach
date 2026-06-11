from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from ml.detector import detect_audio

router = APIRouter()


class AnalysisResult(BaseModel):
    risk_score: int
    alert_level: str
    layer_breakdown: dict


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_audio(audio: UploadFile = File(...)):
    data = await audio.read()
    result = detect_audio(data)
    return AnalysisResult(**result)
