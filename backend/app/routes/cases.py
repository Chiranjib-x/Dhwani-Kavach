"""Case view + forensic evidence packs over the audit log.

GET /api/cases       -> JSON list of recent flagged verdicts.
GET /cases           -> HTML flagged-calls list (links to each report).
GET /api/cases/{id}  -> JSON evidence pack for one call.
GET /cases/{id}      -> HTML evidence report for one call (no audio).
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


def _all_rows() -> list[dict]:
    try:
        with open(audit._PATH, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def _flagged(rows: list[dict], limit: int) -> list[dict]:
    items = [
        r for r in rows
        if r.get("alert_level") in _FLAGGED_LEVELS or r.get("action") in _FLAGGED_ACTIONS
    ]
    return items[-limit:][::-1]  # most recent first


def _find(call_id: str) -> dict | None:
    for r in reversed(_all_rows()):
        if r.get("call_id") == call_id:
            return r
    return None


@router.get("/api/cases")
async def cases(limit: int = 200):
    items = _flagged(_all_rows(), limit)
    return {"count": len(items), "cases": items}


@router.get("/api/cases/{call_id}")
async def case_report(call_id: str):
    r = _find(call_id)
    return r or {"error": "case not found", "call_id": call_id}


@router.get("/cases", response_class=HTMLResponse)
async def cases_page():
    rows = _flagged(_all_rows(), 200)
    body = "".join(
        f"<tr class='{(c.get('action') or '').lower()}'>"
        f"<td><a href='/cases/{c.get('call_id','')}'>{c.get('call_id','')}</a></td>"
        f"<td>{c.get('ts','')}</td><td>{c.get('source','')}</td>"
        f"<td>{c.get('risk_score','')}</td><td>{c.get('alert_level','')}</td>"
        f"<td>{c.get('scam_score','') if c.get('scam_score') is not None else ''}</td>"
        f"<td><b>{c.get('action','')}</b></td></tr>"
        for c in rows
    ) or "<tr><td colspan='7'>No flagged calls yet.</td></tr>"
    return HTMLResponse(_PAGE.format(
        title="Flagged Calls", h1="FLAGGED CALLS — audit trail",
        meta=f"{len(rows)} flagged verdict(s). No audio stored.",
        content=f"<table><thead><tr><th>CALL ID</th><th>TIME (UTC)</th><th>SOURCE</th>"
                f"<th>RISK</th><th>LEVEL</th><th>SCAM</th><th>ACTION</th></tr></thead>"
                f"<tbody>{body}</tbody></table>"))


@router.get("/cases/{call_id}", response_class=HTMLResponse)
async def case_page(call_id: str):
    c = _find(call_id)
    if not c:
        return HTMLResponse(_PAGE.format(title="Not found", h1="CASE NOT FOUND",
                                         meta=call_id, content="<a href='/cases'>← back</a>"))
    layers = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in (c.get("layer_breakdown") or {}).items())
    tactics = ", ".join(c.get("tactics") or []) or "—"
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in [
        ("Call ID", c.get("call_id")), ("Time (UTC)", c.get("ts")),
        ("Source", c.get("source")), ("Risk score", c.get("risk_score")),
        ("Alert level", c.get("alert_level")), ("Novelty", c.get("novelty")),
        ("Scam-script score", c.get("scam_score")), ("Tactics", tactics),
        ("Language", c.get("language") or "—"),
        ("Decision", c.get("action")), ("Reason", c.get("action_reason")),
        ("Mode", c.get("mode")), ("Enforced", c.get("enforced")),
    ])
    content = (
        f"<h3>Verdict</h3><table>{rows}</table>"
        f"<h3>Layer breakdown</h3><table><tr><th>LAYER</th><th>SCORE</th></tr>{layers}</table>"
        f"<h3>Transcript</h3><div class='tx'>{(c.get('transcript') or '—')}</div>"
        f"<p class='muted'>Evidence pack — no audio retained. <a href='/cases'>← all cases</a></p>")
    return HTMLResponse(_PAGE.format(
        title=f"Case {call_id}", h1=f"EVIDENCE PACK — {call_id}",
        meta="Forensic report for dispute / regulatory use.", content=content))


_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Dhwani-Kavach — {title}</title>
<style>
 body{{background:#0F1117;color:#F1F5F9;font:14px system-ui,sans-serif;margin:0;padding:32px}}
 h1{{font-size:18px;letter-spacing:.04em}} h3{{color:#5EEAD4;font-size:13px;margin-top:24px}}
 .muted{{color:#64748B;font-size:12px}} a{{color:#5EEAD4}}
 table{{border-collapse:collapse;width:100%;margin-top:8px}}
 th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.07);font-family:ui-monospace,monospace}}
 th{{color:#64748B;font-weight:500;font-size:11px;letter-spacing:.1em}}
 tr.block td{{color:#FF4D6D}} tr.challenge td{{color:#F59E0B}}
 .tx{{margin-top:8px;padding:12px;background:rgba(255,255,255,.03);border-radius:8px;font-family:ui-monospace,monospace;font-size:12px}}
</style></head><body>
 <h1>{h1}</h1><div class="muted">{meta}</div>{content}
</body></html>"""
