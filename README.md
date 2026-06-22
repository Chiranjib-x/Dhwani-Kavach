# Dhwani-Kavach

Real-time AI audio forensics system for detecting deepfake voices on live banking calls.

## Architecture

5-layer ML pipeline:
1. AASIST neural anti-spoofing
2. Handcrafted MFCC/spectral features
3. Breath pattern detection
4. Phase coherence analysis
5. Liveness challenge

## Quick Start

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend

# Frontend
cd frontend && npm install && npm run dev

# Full stack
docker compose up
```

## Phase Roadmap

Full plan: https://vishalvivek2007.github.io/Dhvani-kavach-plan/ (9 phases, 38 steps).
Status legend: ✅ done · ⚠️ partial · ❌ not started.

| Phase | Scope | Status |
|---|---|---|
| **0** Foundation | Monorepo scaffold, deps, AASIST weights, Docker skeleton | ✅ |
| **1A** Spectrogram pipeline | Audio I/O, mel-spectrogram, handcrafted features | ✅ |
| **1B** Detection layers | AASIST + MFCC, breath, phase-coherence, liveness | ✅ |
| **1C** Ensemble | Weighted vote, GREEN/AMBER/RED banding (Redis pub/sub pending) | ⚠️ |
| **2A** FastAPI backend | `/health`, `POST /api/analyze`, `GET /api/challenge`, `ws /ws/analyze` | ✅ |
| **2B** Streaming pipeline | Backend 10s sliding-window detection over `ws /ws/analyze` ✅ (currently unused by the UI; Redis fan-out + liveness-WS pending) | ⚠️ |
| **3A** Dashboard core | Risk gauge + file-upload analysis UI (Vite). A live-WebSocket streaming dashboard was built then **intentionally replaced** by this simpler UI | ⚠️ |
| **3B** Dashboard polish | Per-layer breakdown shown; live mic capture + alert history removed in the UI simplification; scenario switcher not built | ⚠️ |
| **4** Docker + demo | Production Docker, demo audio pack, smoke test, perf validation | ❌ |

> **Note:** the frontend was deliberately simplified to a Vite file-upload UI (`POST /api/analyze`). The streaming backend (`ws /ws/analyze`) stays available for a future live dashboard but is not currently wired to the UI.

See [`HANDOFF.md`](HANDOFF.md) for full status, function reference, and open decisions.
