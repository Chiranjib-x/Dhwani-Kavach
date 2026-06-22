import asyncio

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ml.detector import detect_samples
from ml.audio_utils import SAMPLE_RATE

router = APIRouter()

_WINDOW = SAMPLE_RATE * 10   # 10s detection window
_HOP = SAMPLE_RATE * 5       # slide 5s forward (50% overlap for continuity)


def _drain_windows(buf: np.ndarray):
    """Pull every full 10s window out of the buffer, sliding 5s each time.
    Returns (windows, leftover) where leftover is the unconsumed tail."""
    windows = []
    while len(buf) >= _WINDOW:
        windows.append(buf[:_WINDOW])
        buf = buf[_HOP:]
    return windows, buf


@router.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket):
    """
    Real-time streaming detection for a live call.

    Send raw 16 kHz mono float32 PCM as binary frames (e.g. Web Audio API
    output). The server accumulates a 10s window, scores it, slides forward
    5s, and emits {risk_score, alert_level, layer_breakdown} per window.
    """
    await websocket.accept()
    buf = np.empty(0, dtype=np.float32)
    try:
        while True:
            data = await websocket.receive_bytes()
            n = len(data) - (len(data) % 4)  # ponytail: drop a partial float, realign next frame
            frame = np.frombuffer(data[:n], dtype=np.float32)
            buf = np.concatenate([buf, frame])

            windows, buf = _drain_windows(buf)
            for w in windows:
                try:
                    # CPU-bound — off the event loop so other streams aren't blocked.
                    result = await asyncio.to_thread(detect_samples, w.copy())
                except Exception as exc:
                    await websocket.send_json({"error": str(exc)})
                    continue
                await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
