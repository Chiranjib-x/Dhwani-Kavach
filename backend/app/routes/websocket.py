from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ml.detector import detect_audio

router = APIRouter()


@router.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket):
    """
    Stream audio chunks for real-time analysis.
    Send raw audio bytes; receive JSON with risk_score, alert_level,
    and layer_breakdown per chunk.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            result = detect_audio(data)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
