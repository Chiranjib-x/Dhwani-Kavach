"""Case view over the audit log — the flagged-calls list a bank's fraud team works.

GET /api/cases -> JSON of recent flagged verdicts (RED/AMBER or CHALLENGE/BLOCK).
GET /cases      -> a self-contained HTML page rendering that list (no frontend build).
ponytail: reads the JSONL audit file directly; move to the bank's DB at integration.
"""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app import audit

router = APIRouter()

_FLAGGED_LEVELS = {"RED", "AMBER"}
_FLAGGED_ACTIONS = {"CHALLENGE", "BLOCK"}


def _load_cases(limit: int = 200) -> list[dict]:
    try:
        with open(audit._PATH, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
    flagged = [
        r for r in rows
        if r.get("alert_level") in _FLAGGED_LEVELS or r.get("action") in _FLAGGED_ACTIONS
    ]
    return flagged[-limit:][::-1]  # most recent first


@router.get("/api/cases")
async def cases(limit: int = 200):
    items = _load_cases(limit)
    return {"count": len(items), "cases": items}


@router.get("/cases", response_class=HTMLResponse)
async def cases_page():
    rows = _load_cases()
    body = "".join(
        f"<tr class='{(c.get('action') or '').lower()}'>"
        f"<td>{c.get('ts','')}</td><td>{c.get('source','')}</td>"
        f"<td>{c.get('risk_score','')}</td><td>{c.get('alert_level','')}</td>"
        f"<td>{c.get('scam_score','') if c.get('scam_score') is not None else ''}</td>"
        f"<td><b>{c.get('action','')}</b></td></tr>"
        for c in rows
    ) or "<tr><td colspan='6'>No flagged calls yet.</td></tr>"
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Dhwani-Kavach — Flagged Calls</title>
<style>
 body{{background:#0F1117;color:#F1F5F9;font:14px system-ui,sans-serif;margin:0;padding:32px}}
 h1{{font-size:18px;letter-spacing:.04em}} .muted{{color:#64748B;font-size:12px}}
 table{{border-collapse:collapse;width:100%;margin-top:16px}}
 th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.07);font-family:ui-monospace,monospace}}
 th{{color:#64748B;font-weight:500;font-size:11px;letter-spacing:.1em}}
 tr.block td{{color:#FF4D6D}} tr.challenge td{{color:#F59E0B}}
</style></head><body>
 <h1>FLAGGED CALLS — audit trail</h1>
 <div class="muted">{len(rows)} flagged verdict(s). No audio stored. Source: append-only audit log.</div>
 <table><thead><tr><th>TIME (UTC)</th><th>SOURCE</th><th>RISK</th><th>LEVEL</th><th>SCAM</th><th>ACTION</th></tr></thead>
 <tbody>{body}</tbody></table>
</body></html>"""
    return HTMLResponse(html)
