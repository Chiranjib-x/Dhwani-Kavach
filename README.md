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

- **Phase 0** — Scaffold + model download (current)
- **Phase 1A** — Audio ingestion pipeline
- **Phase 1B** — AASIST inference
- **Phase 1C** — Layers 2–4
- **Phase 1D** — Liveness challenge
- **Phase 1E** — Ensemble scoring + WebSocket streaming
- **Phase 2** — React dashboard
