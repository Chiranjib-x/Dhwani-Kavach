import asyncio
import time

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ml.detector import detect_samples
from ml.audio_utils import SAMPLE_RATE
from ml import scam_detector
from ml.fusion import fuse
from app import audit

router = APIRouter()

_WINDOW = SAMPLE_RATE * 4    # 4s window — matches the model's training clip length
_HOP = SAMPLE_RATE * 2       # slide 2s forward (50% overlap)
_CONTEXT = SAMPLE_RATE * 8   # transcribe the last ~8s for a fuller transcript
_SCAM_PERIOD = 4.0           # seconds between scam (STT+LLM) runs


def _drain_windows(buf: np.ndarray):
    windows = []
    while len(buf) >= _WINDOW:
        windows.append(buf[:_WINDOW])
        buf = buf[_HOP:]
    return windows, buf


@router.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket):
    """
    Real-time streaming fraud shield for a live call.

    Send raw 16 kHz mono float32 PCM as binary frames. Emits
    {risk_score, alert_level, layer_breakdown, novelty, scam, action,
    action_reason} per scored window.

    Stays real-time under load: only the newest window is scored (backlog is
    discarded), and the scam layer (STT+LLM, heavier) runs in the background so
    it never blocks the verdict loop.
    """
    await websocket.accept()
    buf = np.empty(0, dtype=np.float32)
    recent = np.empty(0, dtype=np.float32)
    scam = {"score": 0, "tactics": [], "transcript": ""}
    scam_task: asyncio.Task | None = None
    last_scam = 0.0
    try:
        while True:
            data = await websocket.receive_bytes()
            n = len(data) - (len(data) % 4)  # ponytail: drop a partial float, realign next frame
            frame = np.frombuffer(data[:n], dtype=np.float32)
            buf = np.concatenate([buf, frame])
            recent = np.concatenate([recent, frame])[-_CONTEXT:]

            windows, buf = _drain_windows(buf)
            if not windows:
                continue
            # Only score the newest window; discarding backlog keeps us real-time
            # and stops a slow CPU from flooding the client with stale verdicts.
            w = windows[-1]

            # Harvest a finished background scam result, if any.
            if scam_task is not None and scam_task.done():
                try:
                    scam = scam_task.result() or scam
                    print(f"[scam] score={scam.get('score')} "
                          f"transcript={scam.get('transcript','')!r}", flush=True)
                except Exception as exc:
                    print(f"[scam] error: {exc}", flush=True)
                scam_task = None

            try:
                result = await asyncio.to_thread(detect_samples, w.copy())
            except Exception as exc:
                await websocket.send_json({"error": str(exc)})
                continue

            # Kick off the next scam pass in the background (non-blocking, throttled).
            now = time.monotonic()
            if scam_task is None and now - last_scam >= _SCAM_PERIOD and len(recent) >= _WINDOW:
                last_scam = now
                snap = recent.copy()
                scam_task = asyncio.create_task(asyncio.to_thread(scam_detector.analyze, snap))

            result["scam"] = scam
            result.update(fuse(
                deepfake_risk=result["risk_score"],
                scam_score=scam.get("score", 0),
                novelty=result.get("novelty", 0.0),
            ))
            audit.record("ws", result)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
    finally:
        if scam_task is not None:
            scam_task.cancel()
