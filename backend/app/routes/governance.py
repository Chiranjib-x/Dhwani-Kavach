"""Governance routes — labelling, FPR/TPR, drift, model registry dashboard.

POST /api/cases/{id}/label?label=fraud|legit  -> analyst label (API)
GET  /cases/{id}/label/{label}                -> label + redirect (HTML convenience)
GET  /api/governance                          -> {confusion, drift, models}
GET  /governance                              -> HTML dashboard
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from app import governance
from app.routes.cases import _PAGE

router = APIRouter()


@router.post("/api/cases/{call_id}/label")
async def label_api(call_id: str, label: str = "fraud"):
    return {"call_id": call_id, "label": governance.label_case(call_id, label)}


@router.get("/cases/{call_id}/label/{label}")
async def label_redirect(call_id: str, label: str):
    governance.label_case(call_id, label)
    return RedirectResponse(url=f"/cases/{call_id}", status_code=303)


@router.get("/api/governance")
async def governance_api():
    return {"confusion": governance.confusion(), "drift": governance.drift(),
            "models": governance.registry().get("models", [])}


@router.get("/governance", response_class=HTMLResponse)
async def governance_page():
    c, d = governance.confusion(), governance.drift()
    models = governance.registry().get("models", [])

    cm = (f"<table><tr><th></th><th>actual fraud</th><th>actual legit</th></tr>"
          f"<tr><td>flagged</td><td>{c['tp']} (TP)</td><td>{c['fp']} (FP)</td></tr>"
          f"<tr><td>passed</td><td>{c['fn']} (FN)</td><td>{c['tn']} (TN)</td></tr></table>"
          f"<p class='muted'>{c['labeled']} labelled · "
          f"TPR (detection) {c['tpr']} · FPR (false alarm) {c['fpr']} · precision {c['precision']}</p>")

    if d.get("enough_data"):
        col = "#FF4D6D" if d["alert"] else "#22C55E"
        dr = (f"<p>baseline flag-rate {d['baseline_flag_rate']} → recent {d['recent_flag_rate']} "
              f"(<span style='color:{col}'>drift {d['drift']}{' · ALERT' if d['alert'] else ' · stable'}</span>, "
              f"n={d['n']})</p>")
    else:
        dr = "<p class='muted'>Not enough verdicts yet to assess drift.</p>"

    reg = "".join(
        f"<tr class='{'block' if m.get('status')=='champion' else ''}'>"
        f"<td>{m.get('version')}</td><td>{m.get('status')}</td><td>{m.get('date')}</td>"
        f"<td>{', '.join(m.get('training_data', []))}</td><td>{m.get('eval')}</td></tr>"
        for m in models) or "<tr><td colspan='5'>No models registered.</td></tr>"

    content = (
        f"<h3>Confusion matrix (from analyst labels)</h3>{cm}"
        f"<h3>Verdict drift</h3>{dr}"
        f"<h3>Model registry</h3><table>"
        f"<tr><th>VERSION</th><th>STATUS</th><th>DATE</th><th>TRAINING DATA</th><th>EVAL</th></tr>{reg}</table>"
        f"<p class='muted'>Label calls from their <a href='/cases'>evidence pages</a> to populate TPR/FPR.</p>")
    return HTMLResponse(_PAGE.format(
        title="Governance", h1="MODEL GOVERNANCE — risk monitoring",
        meta="TPR/FPR from analyst labels · verdict drift · model registry (champion/challenger).",
        content=content))
