"""Campaign view — fraud rings, where the same synthetic voice hit many calls.

GET /api/campaigns -> JSON clusters (voice hit >= N calls).
GET /campaigns     -> HTML page listing campaigns and their linked calls.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app import voiceprints
from app.routes.cases import _PAGE

router = APIRouter()


@router.get("/api/campaigns")
async def campaigns(min_size: int = 2):
    items = voiceprints.campaigns(min_size)
    return {"count": len(items), "campaigns": items}


@router.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page():
    items = voiceprints.campaigns(2)
    blocks = []
    for c in items:
        calls = "".join(
            f"<tr class='{(m.get('action') or '').lower()}'>"
            f"<td><a href='/cases/{m['call_id']}'>{m['call_id']}</a></td>"
            f"<td>{m['ts']}</td><td>{m['risk']}</td><td>{m['action']}</td></tr>"
            for m in c["calls"])
        blocks.append(
            f"<h3>Campaign {c['cluster_id']} — {c['hits']} calls "
            f"({c['flagged_hits']} flagged), last seen {c['last_seen']}</h3>"
            f"<table><tr><th>CALL ID</th><th>TIME (UTC)</th><th>RISK</th><th>ACTION</th></tr>{calls}</table>")
    content = "".join(blocks) or "<p class='muted'>No campaigns yet — needs 2+ calls from the same voice.</p>"
    return HTMLResponse(_PAGE.format(
        title="Campaigns", h1="FRAUD CAMPAIGNS — same voice, many calls",
        meta=f"{len(items)} active campaign(s). The same synthetic voiceprint across multiple calls.",
        content=content))
