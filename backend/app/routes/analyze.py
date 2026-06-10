from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

router = APIRouter()

class AnalysisResult(BaseModel):
    risk_score: int
    alert_level: str
    layer_breakdown: dict

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_audio(audio: UploadFile = File(...)):
    # TODO: Phase 1C - wire in detect_audio()
    return AnalysisResult(
        risk_score=0,
        alert_level="GREEN",
        layer_breakdown={"aasist": 0, "mfcc": 0, "breath": 0, "phase": 0, "liveness": 0}
    )
