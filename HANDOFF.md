# Dhwani-Kavach — Handoff / Context

Real-time AI audio-forensics system that flags deepfake / synthetic voices on
banking calls. 5-layer detection pipeline (one trained neural model + four
signal-processing heuristics), FastAPI backend, Next.js dashboard.

This file is the single source of truth for **where the project stands** and
**how to continue**. Read it top to bottom before touching code.

---

## 0. START HERE — current state (updated 2026-07)

> Sections 1–10 below are **historical** (they describe the original AASIST.pth +
> Next.js build). The project has since migrated to an **XLS-R + W2VAASIST** neural
> detector and a **Vite/TanStack** frontend. Where §1–10 disagree with this section,
> **this section wins.** The app-flow, API contracts, and "how to run the backend"
> parts of §1–10 are still broadly correct.

### The detector today
- **Model:** `facebook/wav2vec2-xls-r-300m` backbone truncated to its first 5 encoder
  layers + a **W2VAASIST** graph-attention head. Code: `backend/ml/detector_v2.py`.
- **Deployed weights:** a single fine-tuned bundle `backend/models/w2v2aasist_full.safetensors`
  (~306 MB, backbone + head). The backend auto-loads it (or `DHWANI_MODEL=<path>`).
- **Fallback:** if the bundle is absent, it falls back to the head-only
  `backend/models/w2v2aasist_cotrain.safetensors` (**in git**) on a stock XLS-R backbone —
  runs, but less robust. **Do not pair the new `calibration.json` with this fallback** (it
  would mis-scale it and over-flag).

### ⚠️ A fresh clone has NO working model — read this first
Two files are **gitignored** (too big / paired with the bundle), so your clone won't have them:
| file | what | how to get it |
|---|---|---|
| `backend/models/w2v2aasist_full.safetensors` (306 MB) | the fine-tuned detector | **re-run the Kaggle training** (below), or get the file from Vishal |
| `backend/models/calibration.json` | maps the bundle's scores → alarm scale | comes with the bundle; get it from Vishal, or refit (below) |

Until you drop those two in `backend/models/`, the app runs on the weaker fallback head.
**The bundle + calibration must travel together** — the calibration is fit to that exact model.

### How to run (verified this session)
```bash
# Backend → http://localhost:8000
python -m uvicorn app.main:app --app-dir backend --port 8000
# Frontend → http://localhost:5173 (Vite)
cd frontend && npm install && npm run dev
```
> The backend loads the model into memory **at startup**. If you swap the model or
> calibration files, **restart the backend** — it will not hot-reload them.

### Does it work? (measured on Vishal's real clips, `sample_audio/`)
- ✅ **Flags fakes:** all 10 clone clips → 🔴 RED.
- ✅ **Own-voice reals:** GREEN/AMBER (no false RED).
- ❌ **Known weakness:** 2 out-of-domain English *studio* real voices (`lily_original`,
  `chris_original`) false-positive as fake — `lily` even scores above her own clone.
  Calibration can't fix inverted scores; this needs **more diverse real training data**.
- Calibration is **provisional** — fit on ~30 clips. Refit it on a bigger labeled
  real+fake set for production (see "Retrain / improve" below).

### Kaggle training pipeline (how the bundle is made)
- Script: `backend/training/train_robust.py` — full fine-tune (backbone lr 1e-5 + head lr 1e-4),
  on-the-fly telephony-weighted channel augmentation, per-condition + per-source held-out gate,
  saves the best **full bundle** to `--out`. Now includes **label smoothing + class-balanced
  sampling** (reduces the over-confidence that made calibration fragile).
- Run it on Kaggle GPU via one self-contained cell (clone repo → pip install → symlink datasets
  → `python -m training.train_robust --data <dir> --out /kaggle/working/w2v2aasist_full.safetensors --epochs 6`).
  Datasets used: ASVspoof2019 LA, Common Voice Hindi, In-The-Wild, Fake-or-Real, + Vishal's own
  voices folded in. Download the 306 MB bundle from Kaggle Output when done.
- **Deploy:** A/B locally first — `DHWANI_MODEL=<new.safetensors> python -m eval.run eval/corpus --telephony`
  — then copy over `backend/models/w2v2aasist_full.safetensors` only if it wins, and refit calibration.

### Retrain / improve (next tickets, evidence-based)
1. **Kill the studio-voice false positives** → add more **diverse real English/varied-mic**
   speakers to the Kaggle `real/` folder (and/or the MLAAD multilingual set). This is the
   highest-value lever per the generalization literature.
2. **Stronger head** (bigger lift) → swap W2VAASIST for an **SLS or Mamba** classifier on the
   same XLS-R backbone; these top the In-The-Wild generalization leaderboard.
3. **Refit calibration** on a real labeled set (`backend/ml/scoring.py` Platt `a,b` + `t_low/t_high`;
   clamp for `b` was widened to ±8 for the compressed fine-tuned scores).
   - Research: Speech DF Arena (arXiv 2509.02859), Understanding Generalization (arXiv 2406.03512).

### Key files (current detector)
```
backend/ml/detector_v2.py        active detector (XLS-R + W2VAASIST bundle loader)
backend/ml/scoring.py            Platt calibration + StreamAggregator (EWMA/hysteresis)
backend/ml/ensemble.py           neural-dominant fusion (0.90 neural / 0.10 heuristics)
backend/training/train_robust.py Kaggle fine-tune pipeline (the bundle factory)
backend/tools/augment.py         telephony/reverb/noise channel augmentation
backend/eval/run.py              A/B eval harness (per-channel EER/AUC on a labeled corpus)
backend/models/                  w2v2aasist_cotrain.safetensors (in git, fallback head);
                                 w2v2aasist_full.safetensors + calibration.json (GITIGNORED)
frontend/src/components/LiveMonitor.tsx  live mic/file streaming UI
frontend/src/routes/index.tsx            landing page (note: still markets a "5-layer" story)
```

### Honest caveats for whoever takes over
- The landing page (`routes/index.tsx`) still shows **hardcoded demo numbers** (96/91/88/94/97,
  "99.2% accuracy") and a "5 layers, all must agree" story. Reality: it's **one neural model**
  at 90% weight; the 4 heuristic layers are near-noise. Update the marketing to match if you ship.
- `sample_audio/` (Vishal's real + cloned voices) is **gitignored / private** — the labeled set
  used for the numbers above. Ask Vishal for it to reproduce the eval.

---

## 1. Current status against the build plan

Plan: https://vishalvivek2007.github.io/Dhvani-kavach-plan/ (phases 0→4, 38 steps).

| Phase | Steps | Status |
|---|---|---|
| 0 Foundation | 1–5 | ✅ done |
| 1A Spectrogram pipeline | 6–9 | ✅ done |
| 1B 5 detection layers | 10–14 | ✅ done |
| 1C Ensemble + Redis | 15–18 | ⚠️ ensemble done; **Redis pub/sub NOT built** |
| 2A FastAPI backend | 19–22 | ✅ `/health`, `/api/analyze`, `/ws/analyze` (202/background-queue step skipped — superseded by threadpool) |
| 2B Streaming pipeline | 23–25 | ⚠️ sliding-window WS done (23); **Redis fan-out (24) + liveness WS flow (25) deferred** |
| 3A Dashboard core | 26–29 | ✅ live dashboard (adapted to Next.js, not Vite) |
| 3B Dashboard polish | 30–33 | ⚠️ layer bars, mic capture, alert history done; **scenario switcher (33) skipped on purpose** |
| 4 Docker + demo | 34–38 | ❌ not started — needs demo audio + a Docker host |

**Net:** everything through 3B is on `main` and runs. Phase 4 + a few deferred
items remain (see §8).

---

## 2. Architecture / data flow

```
                         ┌─────────────── frontend (Next.js :3000) ───────────────┐
  file upload  ──POST──▶ │ simulation-section.tsx  → POST /api/analyze (one-shot)  │
  file / mic   ──WS────▶ │ dashboard-section.tsx   → ws /ws/analyze (streaming)    │
                         └─────────────────────────────────────────────────────────┘
                                              │
                                   backend (FastAPI :8000)
                                              │
   detect_audio(bytes)  /  detect_samples(np.ndarray)   ← ml/detector.py
        │ decode → chunk into 4s windows → silence-gate → score each → worst chunk wins
        ▼
   5 layers (ml/*.py):  aasist (trained, 60%) · mfcc · breath · phase · liveness (heuristics, 10% each)
        ▼
   ensemble.compute_ensemble → {risk_score 0–100, alert_level GREEN/AMBER/RED}
```

The **worst (highest-risk) 4s chunk drives the verdict** — a deepfake anywhere
in the call flags the whole call. Silent chunks are skipped entirely.

---

## 3. How to run (verified working)

Python 3.11, deps already installed. From the **repo root**:

```bash
# Backend  → http://localhost:8000   (docs at /docs)
python -m uvicorn app.main:app --app-dir backend --port 8000

# Frontend → http://localhost:3000
cd frontend && npm run dev
```

Smoke test (last verified this session):

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"dhwani-kavach-backend"}

curl -F "audio=@some.wav" http://localhost:8000/api/analyze
# {"risk_score":14,"alert_level":"GREEN","layer_breakdown":{"aasist":0,"mfcc":4,"breath":75,"phase":64,"liveness":0}}
```

Run the test suites:

```bash
cd backend
for t in test_audio_utils test_aasist_model test_phase1c test_phase1de test_detector test_streaming; do python tests/$t.py; done
```

Frontend type/build check:

```bash
cd frontend && npx tsc --noEmit && npm run build
```

`docker compose up` exists but is dev-mode (backend uvicorn + frontend `next dev`
+ redis). The redis service runs but **nothing uses Redis yet** (see deferred §8).

---

## 4. API & WebSocket contracts

**`POST /api/analyze`** — multipart form, field name `audio` (a wav/mp3/flac/ogg/webm/m4a file).
Max 25 MB (413 if over, 422 if empty/undecodable). Returns:
```json
{ "risk_score": 0-100, "alert_level": "GREEN|AMBER|RED",
  "layer_breakdown": { "aasist":0-100, "mfcc":0-100, "breath":0-100, "phase":0-100, "liveness":0-100 } }
```

**`GET /api/challenge`** — liveness prompt:
```json
{ "challenge_id":"8hex", "prompt":"Please say the following digits: ...", "digits":[..], "note":"..." }
```
⚠️ Content is **not verified** — no ASR yet. The liveness *score* is acoustic only.

**`ws /ws/analyze`** — streaming. Client sends **raw 16 kHz mono float32 PCM**
as binary frames (NOT encoded audio). Server buffers a 10s window, scores it,
slides forward 5s (50% overlap), and emits one analyze-shaped JSON per window,
or `{"error": "..."}` on a bad frame (the stream stays open).

**`GET /health`** — `{"status":"ok","service":"dhwani-kavach-backend"}`.

CORS is wide open (`allow_origins=["*"]`) — fine for the demo, tighten before prod.

---

## 5. Backend reference (`backend/`)

### `ml/audio_utils.py` — audio I/O & framing
- `SAMPLE_RATE = 16000`, `CHUNK_DURATION = 4.0`, `CHUNK_SAMPLES = 64000`
- `load_audio_bytes(data, sr=16000) -> (np.ndarray float32, sr)` — soundfile, falls back to librosa for mp3/webm/etc.
- `normalize(audio)` — peak-normalize to ±1
- `pad_or_trim(audio, length)` — zero-pad / trim (used by heuristic `preprocess`)
- `repeat_pad(audio, length)` — **tile** to length (ASVspoof/AASIST convention; used by AASIST)
- `chunk_audio(audio, chunk_samples, hop_samples=chunk//2)` — list of 4s windows, 50% overlap
- `preprocess(audio)` = `pad_or_trim(normalize(audio))` — input prep for the heuristic layers

### `ml/detector.py` — orchestration
- `detect_samples(audio: np.ndarray) -> dict` — chunk → **silence-gate** (`_rms ≥ _SILENCE_RMS=1e-3`) → score voiced chunks → worst-chunk verdict. All-silent ⇒ GREEN/0. Caps at `_MAX_CHUNKS=16` (strides across long files).
- `detect_audio(audio_bytes: bytes) -> dict` — decode then `detect_samples`.
- `_score_chunk(model, chunk)` — runs all 5 layers, `nan_to_num` + clip [0,1] on each.
- `_get_model()` — lazy singleton load of AASIST.

### `ml/aasist_model.py` — Layer 1 (trained, 60% weight)
- `load_aasist(path, device="cpu") -> AASISTModel`
- `infer(model, audio, device="cpu") -> float` spoof prob [0,1]. **Feeds raw `repeat_pad`'d waveform, NOT peak-normalized** (matches training).
- Architecture: SincConv front-end + residual encoder + homo/hetero graph-attention (AASIST). Weights in `backend/models/AASIST.pth`.

### Heuristic layers (each `score_*(audio) -> float [0,1]`, higher = more fake)
- `ml/handcrafted.py` `score_handcrafted` — MFCC temporal std, spectral flatness, centroid CV
- `ml/breath_detector.py` `score_breath` — counts breath-like low-energy broadband events
- `ml/phase_coherence.py` `score_phase` — temporal variance of STFT phase deviation
- `ml/liveness.py` `score_liveness` (+ `generate_challenge`) — pitch jitter, noise floor, syllabic AM depth

### `ml/ensemble.py`
- `WEIGHTS = {aasist:.60, mfcc:.10, breath:.10, phase:.10, liveness:.10}` (must sum to 1)
- `compute_ensemble(layer_scores) -> {risk_score, alert_level}` — bands: **GREEN <40, AMBER 40–69, RED ≥70**

### `app/`
- `main.py` — FastAPI app, CORS, routers, `/health`
- `routes/analyze.py` — `POST /api/analyze`; 25 MB cap; runs `detect_audio` via `asyncio.to_thread` (keeps event loop free)
- `routes/challenge.py` — `GET /api/challenge`
- `routes/websocket.py` — `ws /ws/analyze`; `_WINDOW=10s`, `_HOP=5s`, `_drain_windows(buf)` pulls full windows; off-thread inference, per-frame error isolation

### `ml/spectrogram.py`
Mel/MFCC tensor helpers — used by tests only, **not** in the live detection path.

---

## 6. Frontend reference (`frontend/`)

Next.js 16 / React 19 / Tailwind v4 / framer-motion. `NEXT_PUBLIC_API_URL`
(default `http://localhost:8000`) sets the backend; the WS URL is derived from it.

- `lib/use-websocket.ts` — `useWebSocket(url, onMessage) → {status, send, reconnect}`. Auto-connect, capped reconnect (6× / 1.5s), binary send-queue until open, parses JSON frames.
- `lib/audio-stream.ts` — `TARGET_SR=16000`; `decodeTo16kMono(file) → Float32Array` (native `OfflineAudioContext` resample, no lib); `streamPcm(pcm, send, opts)` paced frame sender.
- `lib/use-mic-stream.ts` — `useMicStream(onFrame) → {start()→AnalyserNode, stop()}`. `getUserMedia` → `AudioContext({sampleRate:16000})` → `ScriptProcessorNode` → 16 kHz float32 frames.
- `components/dashboard-section.tsx` — **live** dashboard: file streaming **and** mic mode → `/ws/analyze`; risk gauge, scrolling 128-band spectrogram (`AnalyserNode`), per-layer bars, timestamped alert-history log, connection-status dot.
- `components/simulation-section.tsx` — separate one-shot file-upload UI → `POST /api/analyze`.
- `app/page.tsx` — section order: Hero, Attack, Layers, **Dashboard**, **Simulation**, Footer.

> The dashboard's WS/mic/spectrogram path is **only build/tsc-verified**, never
> exercised in a real browser yet. First continuation task: open it with the
> backend running and confirm live streaming, mic capture, and the canvas.

---

## 7. Tests

Plain `assert`-based scripts (no pytest needed), run directly:

| File | Covers |
|---|---|
| `tests/test_audio_utils.py` | load/normalize/pad/`repeat_pad`/chunk/preprocess + spectrogram helpers |
| `tests/test_aasist_model.py` | AASIST load, forward shapes, infer range/determinism, batch consistency |
| `tests/test_phase1c.py` | layers 2–4 |
| `tests/test_phase1de.py` | liveness, ensemble weights/bands, full `detect_audio` |
| `tests/test_detector.py` | worst-chunk verdict, chunk cap/stride, **silence→GREEN gating** |
| `tests/test_streaming.py` | WS sliding-window accumulator (`_drain_windows`) |

All green as of `eae040e`.

---

## 8. Open decisions & what to do next

**Decisions waiting on the team (no code change made unilaterally):**
1. **Ensemble weights & risk bands** — code uses AASIST **60/10/10/10/10**, RED **≥70**; the plan says **40/20/15/15/10**, RED **≥61**. Pick one. (Changing it means updating `ensemble.py` + the band asserts in `test_phase1de.py`.)

**Deferred features (clear next tickets):**
2. **Redis pub/sub fan-out** (plan steps 17, 24) — only needed if multiple dashboards watch one call. `redis` is already in compose + requirements.
3. **ASR liveness** (step 25) — integrate Whisper so `/api/challenge` can verify the caller actually spoke the digits; today liveness is acoustic-only.
4. **Scenario switcher** (step 33) — skipped on purpose: it hardcoded 8/94/78 scores, the synthetic data deliberately removed in "Phase 1F". If wanted, ship 3 *real* sample clips that genuinely produce those verdicts instead.

**Phase 4 (needs assets/hardware the repo can't provide):**
5. Production Docker (nginx build), demo audio pack (real voice + ElevenLabs clone + custom TTS), Docker smoke test, perf validation (<10s e2e, 5 concurrent), README. See the Phase-4 prerequisite checklist that was shared separately.

**Accuracy:**
6. **No real-vs-deepfake ROC has been measured** — impossible without a labeled
   audio set. The heuristic thresholds (`handcrafted.py`, `breath_detector.py`,
   `phase_coherence.py`, `liveness.py`) are hand-tuned guesses. Once you have
   labeled real + fake samples, calibrate those cutoffs and report a real number.

---

## 9. Changes made this session (PRs on `main`)

| PR | Commit | What |
|---|---|---|
| #2 | `6580dc0` | **Whole-recording analysis** — was scoring only the first 4s. Now chunks the full file, worst-chunk verdict. Inference moved off the event loop (`asyncio.to_thread`), 25 MB upload cap, WS per-frame error handling, dead code removed. |
| #4 | `b15f289` | **Phase 2B streaming** — split `detect_samples(ndarray)` / `detect_audio(bytes)`; rewrote `/ws/analyze` into a 10s sliding-window (5s hop) streaming endpoint over raw float32 PCM. |
| #5 | `4187455` | **Phase 3A** — `useWebSocket` hook, `audio-stream` decode/resample, turned the static dashboard mockup into a live one (gauge + layer bars + spectrogram + status dot). |
| #6 | `909c54d` | **Phase 3B** — `useMicStream` (live mic → 16 kHz PCM → WS), mic mode + timestamped alert-history log. |
| #7 | `22f9fdc` | **Accuracy** — AASIST fed raw repeat-padded waveform (training distribution); silence gating (digital silence was false-flagging 46/AMBER → now 0/GREEN); NaN/range guards on every layer score. |

(PR #3 was a mis-targeted duplicate of #4 — ignore it.)

---

## 10. Environment / workflow gotchas

- **OS:** Windows. Shell examples assume git-bash; PowerShell also available.
- **Pushing to `main` is blocked by the dev harness** — work via feature branch → PR → merge. Pure `git push origin main` will be denied.
- Commits in this session are authored **`chiranjib-x`** with **no AI attribution** (team preference).
- `next dev` regenerates `frontend/next-env.d.ts` — discard that stray diff. `*.tsbuildinfo` is gitignored.
- Two lockfiles exist (`/package-lock.json` + `frontend/pnpm-lock.yaml`) → harmless Next.js "inferred workspace root" warning. The frontend installs via npm.
- The **WS contract is raw float32 PCM**, not an encoded audio blob — don't send a `.wav` over the socket; decode to PCM first (see `audio-stream.ts`).
- AASIST model file: `backend/models/AASIST.pth` (already present, loads on first `/api/analyze`).
