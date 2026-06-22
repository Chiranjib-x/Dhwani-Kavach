import asyncio

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
            try:
                # CPU-bound — off the event loop so other connections aren't blocked.
                result = await asyncio.to_thread(detect_audio, data)
            except Exception as exc:
                # One malformed chunk shouldn't tear down the whole stream.
                await websocket.send_json({"error": str(exc)})
                continue
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
