"""WebRTC signaling relay — the ONLY server piece the live-call demo needs.

The two browsers ("customer" + "agent") establish a peer-to-peer WebRTC audio
call directly; the media never touches this server. All we do is relay the SDP
offer/answer and ICE candidates between the (up to 2) peers sharing a room name,
plus a join/leave notice so a client knows when to start negotiating.

This is deliberately NOT a media server (no Janus/mediasoup). The agent taps the
received audio track locally and streams 16 kHz PCM to /ws/analyze -- so the call
audio reaches the detector DIGITALLY, avoiding the over-the-air replay gap that
makes a laptop-mic-hears-a-speaker demo unreliable.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# room name -> set of connected signaling sockets. In-memory, single-process:
# fine for a demo; put it in Redis only if you ever run more than one backend.
_rooms: dict[str, set[WebSocket]] = {}
_MAX_PEERS = 2  # a call has two ends; reject a third so signaling stays unambiguous


async def _send(ws: WebSocket, obj: dict) -> None:
    try:
        await ws.send_text(json.dumps(obj))
    except Exception:
        pass


@router.websocket("/ws/rtc/{room}")
async def rtc_signal(ws: WebSocket, room: str):
    await ws.accept()
    peers = _rooms.setdefault(room, set())
    if len(peers) >= _MAX_PEERS:
        await _send(ws, {"type": "full"})
        await ws.close(code=1008)
        return
    peers.add(ws)
    # The newcomer learns whether a peer is already waiting (so exactly one side
    # initiates the offer); existing peers learn someone joined.
    await _send(ws, {"type": "joined", "peers": len(peers) - 1})
    for p in peers:
        if p is not ws:
            await _send(p, {"type": "peer-joined"})
    try:
        while True:
            msg = await ws.receive_text()  # {type: offer|answer|ice, ...} — relayed verbatim
            for p in list(peers):
                if p is not ws:
                    await _send(p, json.loads(msg))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        peers.discard(ws)
        for p in list(peers):
            await _send(p, {"type": "peer-left"})
        if not peers:
            _rooms.pop(room, None)
