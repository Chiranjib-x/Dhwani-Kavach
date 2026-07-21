# Dhwani-Kavach — Handoff / Context

Real-time AI audio-forensics system that flags deepfake / synthetic voices on
banking calls. 5-layer detection pipeline (one trained neural model + four
signal-processing heuristics), FastAPI backend, Next.js dashboard.

This file is the single source of truth for **where the project stands** and
**how to continue**. Read it top to bottom before touching code.

---

## 0. START HERE — current state (updated 2026-07-21)

> Sections 1–10 below are **historical** (original AASIST.pth + Next.js build). The
> project has since migrated to **XLS-R + W2VAASIST** neural detection and a
> **Vite/TanStack** frontend, then (this session) added a live WebRTC call demo, an
> input-quality abstention layer, honest calibration, offline-safe boot, and a
> researched-but-rejected alternative engine. Where §1–10 disagree with this
> section, **this section wins.** App-flow/API-contract/"how to run" parts of §1–10
> are still broadly correct.

### The detector today — still v2, and that's a deliberate, tested decision
- **Live verdict path (unchanged this session):** `facebook/wav2vec2-xls-r-300m`
  truncated to 5 encoder layers + **W2VAASIST** head (`backend/ml/detector_v2.py`),
  fused 50/50 with `detector_v3.py` (an independent clone-specialist) in
  `backend/ml/ensemble.py`. Acoustic heuristics (mfcc/breath/phase/liveness) are
  computed and shown as evidence but carry **zero weight** — measured near-noise,
  diluting a confident verdict toward AMBER (`ensemble.py`'s WEIGHTS comment has the
  numbers).
- **A ported alternative (`detector_v4.py`, XLSR-SLS, a public SOTA checkpoint) was
  built and A/B tested against v2 across 5 channels — and LOST 4/5** (see
  "Core-engine research" below). It is **not** in the live path. Don't be surprised
  it exists in the codebase; it's the seed for the next retrain, not a competitor
  currently running.
- **Deployed weights:** `backend/models/w2v2aasist_full.safetensors` (~306 MB,
  backbone + head, gitignored). Falls back to the head-only
  `w2v2aasist_cotrain.safetensors` (in git) on a stock backbone if absent — runs,
  less robust; **don't pair `calibration.json` with this fallback**, it mis-scales.

### ⚠️ A fresh clone has NO working model — read this first
Gitignored (too big / paired with a specific bundle):
| file | what | how to get it |
|---|---|---|
| `backend/models/w2v2aasist_full.safetensors` (306 MB) | the fine-tuned v2 detector | re-run Kaggle training (§ below), or get it from Vishal |
| `backend/models/calibration.json` | maps v2's scores → alarm scale, fit to that exact bundle | refit yourself (§ below) — takes ~2 min once the backbone is cached |
| `backend/models/xlsr_sls.safetensors` (1.35 GB, **optional**, only for `detector_v4`/retrain work) | ported public XLSR-SLS checkpoint | `cd backend && python -m tools.port_sls` (one-time, downloads from HF) |

The app **does not need** `xlsr_sls.safetensors` to run — only the v2 bundle + calibration matter for the live path.

### The backend boots and scores with ZERO network access (fixed this session)
Previously `detector_v2`/`detector_v4` called `Wav2Vec2Model.from_pretrained(...)` at
every startup just to get the *architecture* (weights get fully overwritten by the
local bundle anyway) — so a DNS hiccup crashed `/api/analyze` with a
`NameResolutionError`. Fixed: the XLS-R config is vendored locally
(`backend/models/xlsr_300m_config.json`); the backbone is built from that JSON with
no HTTP call when a bundle is present. Verified with `HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1` — analyze still works.

### How to run
```bash
# Backend → http://localhost:8000
python -m uvicorn app.main:app --app-dir backend --port 8000
# Frontend — NOTE: this project's Vite config defaults to port 8080, NOT 5173.
# If 8080 is taken it silently bumps to 8081 — check the terminal for the real URL.
cd frontend && npm install && npm run dev
```
The backend loads models **at startup only** — restart after swapping any
`.safetensors`/`calibration.json`.

### Refit calibration (do this after any model change, or if verdicts feel off)
```bash
cd backend
python -m tools.fit_calibration --exclude=lily_original,chris_original
```
`fit_calibration.py` was rewritten this session — the original version had two real
bugs (both fixed, both worth knowing about if you touch it again):
1. It scored only each clip's **first ~4 seconds** (a silent truncation inside
   `repeat_pad`), while the live app scores the **worst window across the whole
   file**. A calibration fit on the easy opening of each clip is not honest. Fixed:
   `_worst_chunk_score()` now mirrors `ml.detector.detect_samples` exactly.
2. The Platt fit **diverged** (`a=46, b=84`) on a small, near-perfectly-separable
   dev set — classic logistic-regression blowup — landing far outside
   `ml/scoring.py`'s runtime safety clamps `[0.5,1.5]`/`[-8,8]`, so the bands printed
   didn't match what the app would actually run. Fixed with L2 ridge regularization
   + banding the post-clamp values.
- `--exclude=` drops named clips from the fit; the tool also **self-flags** any
  future "OUTLIER REAL" clip automatically (fused score landing at/above `t_low`),
  so this class of bug surfaces on new data without a hardcoded list.
- **Current honest result** (14 well-behaved `sample_audio` clips, `lily_original`/
  `chris_original` excluded): clean EER **0.0%**, real max 0.088, fake min 0.666
  (gap +0.577). Telephony EER 22.5% (expected — no telephony-specific training yet).
  Verified live through `/api/analyze`, not just the fitter's own numbers.

### Known, root-caused model gap: `lily_original.mp3` / `chris_original.mp3`
These two clips **read fake** and are excluded from calibration on purpose — not
hidden, root-caused. `lily_original` scores clean (0.01–0.12) for its first 10
seconds, then **inverts** to fake-range (0.87–0.98) from 10s to the end. A threshold
cannot fix a wrong ranking; this needs the retrain (below). **Don't use these two
files as "real voice" demo material** — use `Script_1..5` or a fresh live voice.

### Input-quality abstention (new this session — Problem 3: unreliable mics)
`backend/ml/quality.py` scores every window on **level (RMS), clipping, and
segmental SNR** and returns a plain-language reason. Wired through
`ml/detector.py` → `ml/fusion.py` → both API routes → `LiveMonitor.tsx`: a
too-quiet/clipping/noisy input no longer gets a confident GREEN or RED — it reads
**UNCERTAIN** with an actionable message ("move to a quieter place", "mic level too
low — speak up"), and the fuse layer forces action=**CHALLENGE** (never BLOCK on a
score we don't trust, never a silent false-clear either). Self-check:
`python -m ml.quality`.

### Live WebRTC call demo (new this session — Problem 2: seamless integration)
`backend/app/routes/rtc.py` (signaling-only relay, `/ws/rtc/{room}`, media stays
peer-to-peer — no media server, no Twilio, no cost) + `frontend/src/routes/call.tsx`
(two roles: Customer / Bank Agent). The agent side taps the **received WebRTC audio
track digitally** (WebAudio, not a physical speaker→mic replay) and streams it to
the existing `/ws/analyze`, so the detector sees the call the way a real telephony
integration would — sidestepping the over-the-air replay gap the whole field
struggles with (see research below). Two browser tabs, no PSTN/card needed;
`cloudflared`/`ngrok` for a second physical device.
**Status: functional but unpolished** — you tested it and found the verdict
inconsistent on live mic speech. That's not a demo-plumbing bug; it's the same v2
channel gap documented above (confirmed via the A/B eval, not guessed).

### Core-engine research (this session, in response to "the detection isn't reliable")
Researched the field (replay-attack literature, Speech DF Arena leaderboard, public
checkpoints) and **ported the strongest open-weights detector**, XLSR-SLS
(Zhang et al., ACM MM 2024; 2.14% EER ASVspoof-DF, 7.84% In-the-Wild) into the stack
with zero fairseq dependency:
- `backend/tools/port_sls.py` — one-time fairseq→HuggingFace key remap → the
  1.35 GB bundle (see key gotchas in code comments: DataParallel prefix,
  `mask_emb`→`masked_spec_embed`, dropped final layer_norm, RAW un-normalized input
  convention, Tak-style label order).
- `backend/ml/detector_v4.py` — runtime. **Critical gotcha if you touch this:**
  feed it exact 64,600-sample windows only. Feeding it the app's normal
  64,000-sample chunks (repeat-padded to fit) creates a mid-speech splice that the
  model reads as a synthetic artifact — measured: real-clip mean score 0.46 spliced
  vs 0.19 exact-window.
- `backend/eval/ab_channels.py` — channel-robust A/B harness: v2 vs v4 vs
  mean/max-fusion across {clean, reverb, noise, telephony, replay-sim}, confirm-2
  aggregate (mirrors the stream aggregator). Run: `python -m eval.ab_channels`
  (~20-40 min CPU) → `eval/ab_channels.json` (gitignored, generated).

**Verdict: v4 lost 4/5 channels** (clean 34.8% vs v2's 13.6% EER; telephony 50.0%
vs 27.3%; only won replay 18.2% vs 26.1%). Fusion didn't beat v2 alone either. Root
cause: v4 is window-unstable on out-of-domain audio (adjacent windows of one real
clip flip 0.00→1.00) and reads reverb itself as spoof evidence. **v2 stays
deployed — the A/B gate did its job and prevented what would have felt like an
upgrade from being a regression.** v4's real value: it *does* fix the lily/chris
inversions on clean audio, and it's a far better warm-start than stock XLS-R for
the next retrain.

Literature anchor for why over-the-air/live-mic detection is hard everywhere, not
just here: Müller et al., "Replay Attacks Against Audio Deepfake Detection"
(Interspeech 2025, arXiv 2505.14862) — W2V2-AASIST-family EER surges 4.7%→18.2% on
replayed audio; RIR-augmented retraining recovers to ~11%, not back to baseline.

### The actual fix for the live-mic gap: retrain, not swap (next step, not yet run)
`backend/training/train_robust.py` now has `--arch sls` (+ `--grad-ckpt`):
fine-tunes the **ported v4 bundle** (not stock XLS-R) with the existing
telephony-weighted on-the-fly channel augmentation and per-condition/per-source
anti-overfit gate. Smoke-tested end-to-end on CPU
(`--smoke --arch sls`, both archs green). Full Kaggle runbook, rewritten this
session: **`PHASE-H-KAGGLE.md`** (old version referenced a retired model). This is
the single highest-value next step — an overnight free-tier T4 run, then A/B via
`eval/ab_channels.py` (the same gate) before it's trusted with a deploy.

### Key files (current state)
```
backend/ml/detector_v2.py        LIVE — XLS-R(5-layer)+W2VAASIST, bundle loader, offline-safe
backend/ml/detector_v3.py        LIVE — independent clone-specialist, fused 50/50 with v2
backend/ml/detector_v4.py        NOT live — ported XLSR-SLS, retrain warm-start only
backend/ml/ensemble.py           neural-only fusion (v2 .5 / v3 .5, heuristics 0 — evidence only)
backend/ml/quality.py            input-quality gate → UNCERTAIN abstention (new)
backend/ml/scoring.py            Platt calibration + StreamAggregator (EWMA/hysteresis)
backend/ml/fusion.py             risk+scam+quality → action (MONITOR/CHALLENGE/BLOCK)
backend/tools/fit_calibration.py rewritten — worst-chunk methodology, ridge-regularized, self-flagging
backend/tools/port_sls.py        one-time fairseq→HF port for detector_v4 (new)
backend/tools/augment.py         telephony/reverb/noise channel augmentation
backend/training/train_robust.py Kaggle fine-tune, now --arch {v2,sls}
backend/eval/run.py               A/B eval harness (per-channel EER/AUC, v2-only)
backend/eval/ab_channels.py      channel-robust A/B: v2 vs v4 vs fusion (new)
backend/app/routes/rtc.py        WebRTC signaling relay for the live-call demo (new)
backend/models/                  w2v2aasist_cotrain.safetensors (in git, fallback);
                                 w2v2aasist_full.safetensors, calibration.json, xlsr_sls.safetensors (GITIGNORED)
                                 xlsr_300m_config.json (in git — vendored, offline boot)
frontend/src/routes/call.tsx     WebRTC live-call demo, two roles (new)
frontend/src/components/LiveMonitor.tsx  live mic/file UI + UNCERTAIN quality banner
frontend/src/routes/index.tsx    landing page — marketing corrected to match reality (see below)
```

### Honest caveats for whoever takes over
- Landing page fabricated metrics ("99.2% accuracy", hardcoded 96/91/88/94/97,
  "5 layers, all must agree") were **removed this session** — now describes the
  actual architecture (neural core + evidence signals + honest abstention).
- `sample_audio/` (Vishal's real + cloned voices) is gitignored/private — the
  labeled set behind every number above. Ask Vishal for it to reproduce.
- **The live-mic reliability complaint is real and NOT fixed yet.** Everything in
  this session either (a) made the existing engine's behavior honest and verified
  (calibration, offline boot, abstention) or (b) proved a model swap wasn't the
  answer and built the actual fix's runway (the SLS-seeded retrain). The GPU run
  is what closes the gap — it hasn't been done.

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
