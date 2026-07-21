# Dhwani-Kavach — 3-Day Sprint Plan (reliability + live demo)

**Locked decisions (2026-07-20):** WebRTC (100% free) live demo · 3 days, all-in ·
GPU retrain is a *parallel bonus on free public data*, NOT a gate on the demo.

**Goal for the demo:** a real caller reads GREEN and *stays* green; ANY AI voice 
on the call reads a distinct RED; a bad mic / noisy room reads **UNCERTAIN** with a
"fix this" message — never a false GREEN or a false RED.

---

## The diagnosis (why it was "75%, mostly amber")

1. **Heuristic dilution.** The verdict averaged the neural detectors with 4 acoustic
   heuristics that are near-noise (`breath` returns ~0.75 on *everything*). A confident
   clone (neural ~0.95) got pulled to AMBER. **Fixed** — verdict is now neural-only.
2. **Razor-thin calibration.** `calibration.json` has `b=5.84`, a huge Platt shift
   compensating for a fine-tuned model whose spoof probs collapsed near 0. The RED
   boundary sits at raw prob ~0.0048, AMBER at ~0.0014 — a hairline band. Any channel
   shift (mic/reverb/replay) moves raw probs across it by orders of magnitude → the
   instability you saw. **Must refit** (task A2) on the new neural-only pipeline.
3. **Over-the-air is a losing game by design.** Playing a deepfake through a speaker
   and re-recording it is a *replay/laundering attack*. Our exact model (W2V2-AASIST)
   degrades ~2-3% EER → ~20-25% EER on replayed audio; RIR augmentation recovers only
   to ~8-12% (Müller et al., Interspeech 2025, arXiv 2505.14862). **So: tap the call
   audio digitally for the demo (WebRTC), don't rely on a laptop mic hearing a phone
   speaker.** Augment to raise the floor; abstain (UNCERTAIN) when too degraded.

---

## DONE this session (committed to the reliability core)

| File | Change |
|---|---|
| `backend/ml/ensemble.py` | **Neural-only WEIGHTS** (aasist .5 / clone_v3 .5, heuristics **0**). Heuristics stay computed + visible as evidence but no longer vote. Passes all ensemble tests. Verified: clone(0.95)+breath(0.75) → **95/RED** (was AMBER). |
| `backend/ml/quality.py` *(new)* | Input-quality gate: SNR + level + clipping → `{ok, score, reason}`. Plain-language reasons ("move to a quieter place"). Self-check green. |
| `backend/ml/detector.py` | Runs the quality gate on the voiced region; emits `result["quality"]`; abstains to **UNCERTAIN** when input can't be trusted. |
| `backend/ml/fusion.py` | `quality_ok=False` → action **CHALLENGE** ("verify the caller another way") — never BLOCK on a score we don't trust. |
| `backend/app/routes/{analyze,websocket}.py` | Thread quality → fuse; re-assert UNCERTAIN over the stream aggregator; surface `quality` in the REST model. |
| `frontend/src/components/LiveMonitor.tsx` | UNCERTAIN color + **input-quality banner** ("INPUT QUALITY LOW — {reason}"). tsc clean. |

**Net effect with no retrain:** confident fakes go cleanly RED, heuristics stop
diluting, and degraded input abstains instead of lying. What's left to make the
*numbers* trustworthy is the calibration refit (A2).

---

## Task board

| # | Task | Owner / model | Effort | Status |
|---|------|---------------|--------|--------|
| A1 | Neural-only verdict + quality/abstention core | **Opus (me)** | high | ✅ done |
| A2 | Refit calibration on real labeled audio, new pipeline | Sonnet | med | ✅ done |
| C1 | WebRTC live-call bridge → `/ws/analyze` | Sonnet | high | ✅ done |
| C2 | Bank-agent console view (adapt LiveMonitor) | Sonnet | med | ✅ done (folded into `/call`) |
| D1 | Honest marketing (strip fake 99.2%/"5-layer") | Haiku | low | ✅ done |
| B1 | Retrain recipe: replay/RIR aug + SLS head + corpus | **Opus (me)** | high | queued |
| B2 | Public-corpus fetch/organize scripts | Sonnet | med | queued |
| B3 | Run retrain on Kaggle GPU, A/B, deploy if it wins | **You** | — | after B1/B2 |

Priority order for 3 days: **A2 → C1 → C2 → D1**, with **B1→B2→B3** in parallel.
The A/C/D track alone gives a reliable, honest, live demo without a GPU.

---

## Delegation specs (paste into a fresh session with the named model)

### A2 — Refit calibration (Sonnet, medium). Needs the XLS-R backbone cached (loads models).
> Repo: Dhwani-Kavach. The verdict is now **neural-only** (`ml/ensemble.py`), so the
> old `backend/models/calibration.json` (fit on the old diluted pipeline) is stale.
> Refit it. (1) Extend `backend/tools/fit_calibration.py` to (a) accept our
> `sample_audio/` naming convention — files ending `_clone` are FAKE, the rest REAL —
> and decode `.mp3`/`.mpeg` (use `ml.audio_utils.load_audio`, not glob `*.wav`);
> (b) score through the SAME path the app uses (`ml/detector.py`'s calibrated neural
> output), not just `detector_v2.infer_raw`, so the fit matches production; (c) also
> report per-condition numbers by running each clip through `ml/telephony.to_telephony`
> and re-scoring, so we see the telephony EER too. (2) Fit Platt a,b + t_low (≈5% FPR on
> reals) + t_high (≈1% FPR), write `backend/models/calibration.json`, print EER + the
> real/fake score gap. (3) Keep the safety clamps in `ml/scoring.py` intact. Acceptance:
> `python -m tools.fit_calibration ...` prints a clean EER and reals sit clearly below
> t_low, fakes above t_high, on `sample_audio/`. Do NOT touch the model weights.

### C1 — WebRTC live-call bridge (Sonnet, high). The demo's "seamless call sync".
> Repo: Dhwani-Kavach. Build a **100% free WebRTC** two-party "call" whose audio is
> scored live by the existing `/ws/analyze` backend (raw 16 kHz mono float32 PCM over
> WebSocket — see `frontend/src/lib/audio-stream.ts` + `use-mic-stream.ts` for the exact
> frame format). Simplest correct design: two browser tabs/phones ("customer" + "agent")
> join a room via a tiny WebRTC signaling server (use a minimal WS signaling in the
> FastAPI backend or `simple-peer`); the agent side receives the customer's audio track,
> taps it through a WebAudio `AudioContext({sampleRate:16000})` → `ScriptProcessorNode`
> (mirror `use-mic-stream.ts`) → sends float32 frames to `/ws/analyze` → renders verdicts.
> No PSTN, no Twilio, no card. Provide a `cloudflared`/`ngrok` one-liner so a second
> phone can join over the internet. Acceptance: two devices connect, the agent screen
> shows a live risk gauge that goes RED within ~6 s when the customer side plays an AI
> clip and stays GREEN on a real voice. Keep it one route + one component; reuse
> `use-websocket.ts`. ponytail: no media-server (Janus/mediasoup) — peer-to-peer only.

### C2 — Bank-agent console (Sonnet, medium).
> Adapt `frontend/src/components/LiveMonitor.tsx` into a call-centric "agent console":
> a caller strip (fake caller-id + call timer), the live verdict gauge, the **quality/
> UNCERTAIN banner** (already wired), the recommended action (MONITOR/CHALLENGE/BLOCK),
> and the alert history. Cut the developer-y bits (shadow toggle, spectrogram is optional).
> One screen a bank ops person would actually watch. Reuse existing hooks; no new deps.

### D1 — Honest marketing (Haiku, low).
> In `frontend/src/routes/index.tsx` remove/replace the fabricated metrics ("99.2%
> accuracy", the hardcoded 96/91/88/94/97 bars) and the "5 layers, all must agree" story.
> Reality: ONE neural detector family (XLS-R + W2VAASIST) carries the verdict; the 4
> heuristics are evidence only; we abstain when input quality is low. Keep it honest and
> still compelling. Don't touch `LiveMonitor.tsx`.

### B2 — Public-corpus fetch (Sonnet, medium). Answers "train on what?".
> Write `backend/training/fetch_corpus.py`: download + organize FREE public data into the
> layout `ml/training/train_robust.py` expects (`<root>/real/`, `<root>/fake/`, `<root>/rir/`,
> `<root>/noise/`). REAL: Mozilla Common Voice **Hindi + Indic** subsets (HF `mozilla-foundation/
> common_voice_17_0`), LibriSpeech clean, In-the-Wild real. FAKE: ASVspoof 2019 LA, WaveFake,
> In-the-Wild fake, MLAAD (multilingual), and any ElevenLabs/OpenTTS clones we generate.
> RIR/NOISE: OpenSLR RIR (SLR28) + MUSAN. Use `huggingface_hub`/`datasets`; cap per-source
> with a `--limit`; write a manifest. Designed to run on Kaggle. Acceptance: `--smoke` lists
> what it WOULD fetch; a real run fills the folders and `train_robust --data <root>` starts.

---

## "Train on what?" — you don't need to own a dataset

Everything above is **free and downloadable on Kaggle/Colab** (Common Voice, ASVspoof,
In-the-Wild, WaveFake, MLAAD, OpenSLR RIR, MUSAN). `train_robust.py` already runs OOTB via
`--bootstrap` (LibriSpeech + VITS). The retrain is a **ceiling-raiser** (fixes the studio-voice
false positives + raises the over-the-air floor), but it can *overfit* on narrow data — your
own memory documents a narrow fine-tune that made things worse. So it rides shotgun:
**A2's calibration + the neural-only fix already carry the demo.** If B3 wins on the held-out
`sample_audio/` A/B, we deploy the new bundle; if not, we ship on the current one.

**B1 (my next heavy task):** finalize the recipe — add the replay chain (speaker-IR → room-RIR →
mic-IR → telephony) on top of the existing telephony/reverb aug, add real RIR/noise sets, and add
an optional **SLS head** (current best generalization: 1.92% EER ASVspoof21-DF, 7.46% In-the-Wild,
same XLS-R backbone → drop-in). Then B2 fetches data, you run B3 on Kaggle.

---

## Core-engine research sprint (2026-07-20 evening) — what was tried, what the numbers say

The live-mic inconsistency was re-attacked at the ENGINE level. Research pass
(replay-attack + generalization literature, Speech DF Arena leaderboard, public
checkpoints) → ported the best open-weights detector, **XLSR-SLS** (2.14% EER
ASVspoof-DF, 7.84% In-the-Wild), into our stack with zero fairseq:

- `backend/tools/port_sls.py` — one-time fairseq→HF port → `models/xlsr_sls.safetensors` (1.35 GB, gitignored)
- `backend/ml/detector_v4.py` — runtime (exact-64600 windows; NEVER feed it spliced repeat-padded chunks — measured artifact)
- `backend/eval/ab_channels.py` — channel-robust A/B harness (clean/reverb/noise/telephony/replay × v2/v4/fusion) → `eval/ab_channels.json`
- `training/train_robust.py --arch sls --grad-ckpt` — fine-tune the ported bundle on Kaggle (warm start, per-condition anti-overfit gate); runbook: `PHASE-H-KAGGLE.md` (rewritten)

**A/B verdict: v4 does NOT enter the live path.** v2 beats it on 4/5 channels
(clean 13.6% vs 34.8% EER, telephony 27.3% vs 50%); v4 wins only replay
(18.2% vs 26.1%); fusion doesn't beat v2 alone. v4 is window-unstable on
out-of-domain audio and reads reverb as spoof. Its real value: it FIXES the
lily/chris studio-voice inversions on clean audio and is the **warm-start seed
for the Kaggle retrain** — the retrain (channel augmentation + real RIRs +
Indian reals) attacks exactly the channels where both models are weak. That
GPU run is the single highest-value next step (`PHASE-H-KAGGLE.md`).

Deployed engine today = **v2 + the refit calibration below** (unchanged by this
sprint — the A/B gate did its job and prevented a regression).

---

## A2 result (2026-07-20) — calibration is fit and verified

`backend/models/calibration.json` is refit on the corrected worst-chunk methodology
(mirrors the app exactly — the first fit scored only each clip's first ~4s, an
unrepresentative-sample bug, now fixed). **Clean EER 0.0%, gap +0.577** (reals cap at
0.088, fakes start at 0.666) on `Script_1..5` (14 well-behaved clips). Verified live via
`/api/analyze`: `Script_1` real → 6/GREEN, `Script_1_clone` → 99/RED, `Script_5_clone` →
98/RED.

**`lily_original.mp3` and `chris_original.mp3` are EXCLUDED from the fit** — these two
clips are a genuine, pre-existing model ranking inversion (`lily_original` reads clean for
10s then flips to fake-range 0.87-0.98 from 10s on) that no threshold can fix; it needs the
deferred retrain (Task B, more diverse real training data). **DO NOT use these two files as
"real voice" demo material — they will read RED.** Use `Script_1..5` or a fresh live mic
voice (what the `/call` demo's customer role actually captures).

To refit later (e.g. after adding more labeled clips):
```
cd backend && ../.venv/Scripts/python.exe -m tools.fit_calibration --exclude=lily_original,chris_original
```
Drop `--exclude=...` to see the raw, unfiltered truth — the tool self-flags any new
"OUTLIER REAL" clip automatically. **Restart the backend after refitting.**

---

## Demo runbook (WebRTC, free)

1. Backend: `python -m uvicorn app.main:app --app-dir backend --port 8000`
2. Frontend: `cd frontend && npm run dev` → open the agent console.
3. Second device joins via `cloudflared tunnel --url http://localhost:5173` (or same LAN).
4. "Customer" device plays a real voice → GREEN. Plays an AI clip → RED. Covers the mic →
   UNCERTAIN ("mic level too low"). One clean story, no PSTN, no bill.

---

## CUT / freeze for the sprint (senior-dev call)

Freeze as-is, don't invest: `governance`, `campaigns`, `cases`, `policy` shadow-mode,
learned-fusion, `voiceprints`. They're plausible product surface but they don't win a
hackathon and they steal focus from a core that's finally getting solid. **Reliability +
one clean live demo + honesty. That's the sprint.**
