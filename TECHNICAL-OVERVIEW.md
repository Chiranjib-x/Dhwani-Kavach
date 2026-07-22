# Dhwani-Kavach — Technical Overview (for academic/technical review)

A complete, honest technical description: architecture, algorithms, models,
training, evaluation, engineering decisions, and limitations. Written for a
technical panel that needs to understand *how* and *why* each part works.

Every number in this document is reproducible from the code in this repo
(`backend/tools/fit_calibration.py`, `backend/eval/ab_channels.py`) — none of
it is a marketing figure.

---

## 1. System architecture

A FastAPI service exposing two ingestion paths into one shared detection engine:

```
                          ┌──────────────── Detection engine ────────────────┐
 REST  POST /api/analyze ─┤  audio → [two independent neural detectors        │
 (files, disputes)        │           + 4 acoustic evidence signals]          │
                          │          [scam-script: STT → LLM]                │
 WS   /ws/analyze ────────┤          [novelty]   [voiceprint/campaign]       │
 (live, 4s/2s windows)    │              │                                   │
                          │       [decision fusion + txn context]            │
 WebRTC  /ws/rtc/{room} ──┤                                                   │
 (live-call signaling,    └──────────────┬───────────────────────────────────┘
  media stays P2P)                       ▼
                       {risk_score, alert_level, action, layer_breakdown,
                        quality, scam, novelty, campaign, mode, call_id}
                                         │
                 audit log (JSONL) · metrics (Prometheus) · governance · campaigns
```

- **Backend:** FastAPI + Uvicorn, PyTorch, torchaudio/librosa, transformers.
- **Frontend:** Vite + React (TanStack Router) — file-upload analysis, a live
  mic/WS dashboard, and a WebRTC two-role live-call demo.
- **Design principle:** every advanced layer is **additive and fail-safe** — if a
  dependency (STT, LLM, an optional model file, even network access) is missing,
  that layer returns neutral/degrades gracefully and the core verdict still ships.
  The backend boots and scores with **zero network access** — the SSL backbone's
  architecture is vendored locally as a config file; only its weights (already on
  disk) are needed.

---

## 2. Voice deepfake detection — the core

**Two independent neural detectors**, fused 50/50 — different architectures,
different training objectives, different failure modes, so neither one's blind
spot silently becomes the product's blind spot:

| Detector | Base model | Trained for | Weight |
|---|---|---|---|
| `detector_v2` | wav2vec2-XLS-R-300M (truncated to first 5 encoder layers, verified bit-identical to the full stack's layer-5 hidden state — ~1.8× faster, zero accuracy cost) + a W2VAASIST graph-attention head | Codecfake — a neural-codec/compression-artifact specialist | 0.50 |
| `detector_v3` | wav2vec2-XLSR-53-large | Fine-tuned specifically on modern commercial TTS/clone engines (ElevenLabs, Polly, etc.) — matches the actual clone threat directly | 0.50 |

Four acoustic heuristics (MFCC/spectral flatness, breath-pattern energy, phase
coherence, liveness/articulation) are computed and shown in `layer_breakdown` as
**evidence**, but carry **zero ensemble weight**. This was a deliberate,
measured change: on labeled real/clone pairs, the heuristics did not separate
the two classes (breath returned ~0.75 on nearly everything), and any non-zero
weight pulled a confidently-fake verdict back toward AMBER — the "detects but
never commits" symptom. Demoting them to evidence-only, while keeping them fully
visible to the analyst, fixed it.

**Aggregation over a whole recording:** audio is split into ~4 s chunks (VAD-gated
— see §4); the **worst (highest-fused-risk) chunk drives the verdict** —
semantically, *a deepfake anywhere in the call is a deepfake*.

**Input-quality gate:** every window is scored for level (RMS), clipping
fraction, and segmental SNR. When the input is too quiet, clipping, or noisy to
trust, the verdict is **UNCERTAIN** (not a guessed GREEN or RED) with a
plain-language reason, and the downstream action is forced to **CHALLENGE** —
never a silent false-clear, never a false alarm from a bad mic.

---

## 3. Calibration & evaluation methodology (the part worth reading carefully)

**Metric:** Equal Error Rate (EER) — the operating point where false-accept =
false-reject rate; standard for anti-spoofing, lower is better.

**Calibration** (`backend/tools/fit_calibration.py`) converts a raw neural
softmax probability into a bank-facing risk score via Platt scaling
(`p_calibrated = sigmoid(a·logit(p_raw) + b)`), then sets the GREEN/AMBER/RED
thresholds from a labeled real/clone dev set. Two failure modes we found and
fixed in this process are worth documenting, because they're the kind of
methodology bug that silently inflates reported accuracy:

1. **Scoring the wrong window.** An earlier version scored each dev clip in one
   shot, which — because of how the model pads short inputs — silently only
   evaluated each clip's first ~4 seconds. The deployed app instead scores the
   **worst window across the whole file**. Fitting calibration on the easy
   opening of a clip and deploying worst-window scoring is an apples-to-oranges
   evaluation. Fixed: the fitter now mirrors the deployed scoring path exactly.
2. **Divergent calibration fit.** With a small (15-clip), near-perfectly
   separable dev set, the Platt-scaling logistic regression diverged
   (coefficients `a≈46, b≈84`) — a classic small-sample separability failure —
   landing far outside the runtime safety clamps. Fixed with L2 ridge
   regularization toward the identity mapping.

**Current honest result** (14 well-behaved dev clips, two documented
out-of-domain outliers excluded — see §7): **clean EER 0.0%**, real scores cap at
0.088, fake scores start at 0.666 (gap +0.577). **Telephony EER 22.5%** — this is
the honest number for the un-augmented model; the retrain in progress (§8)
targets exactly this gap.

**Channel-robust A/B** (`backend/eval/ab_channels.py`) scores a broader labeled
set (dev clips + a public LibriSpeech-real/VITS-fake corpus) across five
acoustic channels with a confirm-2 moving-average aggregate (mirroring the live
stream's temporal smoothing):

| Channel | `detector_v2` EER |
|---|---|
| clean | 13.6% |
| reverb | 17.4% |
| noise | 18.2% |
| telephony | 27.3% |
| replay (speaker→room→phone line) | 26.1% |

This is a **wider, harder, more honest** number than the dev-set figure above —
it includes public out-of-domain fakes the dev set doesn't. We report both
because they measure different things: the dev-set number is "does calibration
work on data we understand," the channel grid is "how does the raw model
generalize."

---

## 4. Streaming engine (live calls)

- **Windowing:** raw 16 kHz float32 PCM frames buffer into **4 s windows, 2 s
  hop** (50% overlap) → a fresh verdict roughly every 2 s; first verdict ~4–6 s in.
- **VAD gating (Silero, ONNX):** windows without real speech are skipped before
  paying for a full SSL forward pass — cuts compute on silence/hold-tone and
  removes the noisiest verdicts. Fails open (never gates out real speech) if the
  model is unavailable.
- **Off-thread inference:** CPU-bound torch runs via `asyncio.to_thread` so the
  event loop isn't blocked.
- **Backpressure:** only the newest window is scored; backlog is discarded — a
  slow CPU degrades gracefully instead of flooding the client.
- **`StreamAggregator`:** EWMA smoothing (α=0.35) + two-window confirmation +
  hysteresis (different thresholds to enter vs. leave RED). A single noisy
  window can't flip the verdict; a sustained signal still confirms RED within
  the first ~6 s of speech.
- **Live-call ingest (WebRTC):** `/ws/rtc/{room}` is a minimal signaling relay —
  the call's two participants ("customer"/"agent") negotiate a **peer-to-peer**
  WebRTC audio connection directly; media never touches this server. The agent
  side taps the received track **digitally** (WebAudio) and streams it into the
  same `/ws/analyze` pipeline. This matters: **playing audio through a physical
  speaker into a microphone (over-the-air replay) is a fundamentally harder
  detection problem than tapping the call digitally** — published research
  (Müller et al., "Replay Attacks Against Audio Deepfake Detection," Interspeech
  2025) measures the same detector family degrading from 4.7% to 18.2% EER under
  physical replay. A real telephony integration taps the call digitally too
  (SIPREC/media-fork), so the WebRTC demo path matches production, not a
  laptop-mic party trick.

---

## 5. Scam-script detection (human scammers)

- **Pipeline:** rolling audio → **Whisper** (`faster-whisper`, base, int8 CPU) →
  transcript → **LLM** (NVIDIA Nemotron via the NIM OpenAI-compatible API) →
  `{scam_score, tactics}`.
- **Tactics** (closed set, evidence-required prompt): urgency, authority
  impersonation, isolation, new-beneficiary, sensitive-info (OTP/PIN) request, threat.
- **Throttling:** runs in the background every ~4 s over the last ~8 s of audio,
  folded into the next verdict — never blocks the ~2 s detection cadence.
- **Multilingual:** Whisper auto-detects language; the LLM reasons in Hindi/Hinglish.
- **Fail-safe:** no key / no STT / network error → neutral score; voice detection unaffected.

---

## 6. Decision fusion

Rule-based (deliberately, for auditability — every decision is explainable):

```
quality_ok == False → CHALLENGE  (input too degraded to trust the voice score —
                                   never BLOCK on a score we don't trust, never
                                   a silent false-clear either)
threat     = voice_risk≥70  OR  scam_score≥70  OR  novelty≥0.6
high_value = new_beneficiary OR amount ≥ ₹50,000
action     = BLOCK      if threat and high_value
             CHALLENGE  if threat
             MONITOR    otherwise
```
Each action carries a plain-English reason. Thresholds are tunable per the
bank's risk appetite. (Rationale: a learned policy needs labelled outcome data
the system must first accumulate; the rule layer is the honest v1 and the
fallback.)

---

## 7. Known, root-caused model gap

Two out-of-domain "studio" real voices in the dev set score inverted — one of
them reads clean for its first 10 seconds then flips to fake-range from 10s on.
This was root-caused precisely (not hand-waved): it's a genuine ranking
inversion by the model on unfamiliar recording conditions, not a calibration
artifact — a threshold cannot fix a wrong ranking. Both clips are excluded from
the calibration fit (visibly, with the tool self-flagging any future clip that
shows the same pattern) and documented as needing the retrain below, not a
threshold tweak.

## 8. Why we didn't just swap in a "better" public model

Following the standard playbook of picking the best open-weights checkpoint from
the anti-spoofing literature, we ported **XLSR-SLS** (Zhang et al., ACM MM 2024;
2.14% EER ASVspoof-DF, 7.84% EER on the In-the-Wild generalization benchmark —
among the strongest published open-weights results) into the stack and ran the
same channel-robust A/B harness against it. **It lost on 4 of 5 channels** to the
model already deployed (clean 34.8% vs. 13.6% EER; telephony 50.0% vs. 27.3%) —
it is unstable window-to-window on out-of-domain audio and reads room reverb
itself as spoof evidence. It is **not** in the live decision path. Its real
value: it fixes the studio-voice inversion above on clean audio, so it is now
the warm-start seed for a channel-augmented fine-tune (telephony/reverb/noise
augmentation + real room impulse responses + more diverse real speakers,
`backend/training/train_robust.py --arch sls`) — the actual fix for the
telephony/replay gap, not yet run on GPU. This is the single biggest remaining
accuracy lever.

---

## 9. Novelty / zero-day detection

- **Signal:** the model's own uncertainty. With spoof prob `p`,
  `novelty = 1 − |2p − 1|` (peaks at p=0.5), maxed against cross-detector
  disagreement when both neural detectors are active (two models trained
  differently disagreeing sharply is itself evidence of an unfamiliar case —
  Lakshminarayanan et al., "Deep Ensembles," NeurIPS 2017).
- **Action:** novelty ≥ 0.6 lifts a GREEN verdict to AMBER.
- **Honest limitation:** this is a **softmax-uncertainty heuristic, not true
  out-of-distribution detection.** A calibrated upgrade is embedding-distance OOD
  (Mahalanobis to class centroids) — noted as the upgrade path in code.

---

## 10. Campaign / repeat-attacker detection

- **Voiceprint:** an L2-normalised embedding from the detector's own forward
  pass (no extra inference cost).
- **Correlation:** cosine similarity against stored voiceprints (sqlite). A
  match above threshold clusters as a campaign; a voiceprint from a previously
  flagged call hits a blocklist on its next call.
- **Honest limitations:** the embedding space is not a dedicated
  speaker-verification space, so the match threshold must be calibrated on real
  clones in a pilot; it's a linear scan today — fine for a branch/PoC, needs
  FAISS/pgvector beyond ~100k voiceprints.

---

## 11. Governance, audit, observability

- **Audit log:** append-only JSONL, one line per verdict, stable `call_id`, no
  audio (transcript text only).
- **Confusion matrix:** analyst fraud/legit labels join to audit verdicts → live
  TPR/FPR/precision.
- **Drift:** flagged-rate in a recent window vs. baseline; upgrade path is
  PSI / proper time-series.
- **Model registry:** champion/challenger with version, training data, eval scores.
- **Metrics:** Prometheus exposition (latency, verdict mix, errors).
- **Shadow vs. enforce:** a policy flag — score+log only, or act — for
  risk-free piloting.

---

## 12. Notable engineering decisions

- **Fail-safe composition:** advanced layers degrade to neutral; the core
  verdict always survives a missing dependency, including a missing network
  connection (the backend boots and scores with `HF_HUB_OFFLINE=1`).
- **Offline-safe architecture loading:** the SSL backbone's architecture is
  built from a small vendored config file rather than fetched from HuggingFace
  at every boot — a bank deployment must not need `huggingface.co` reachable to
  start, and a DNS hiccup must not crash a live call's analysis.
- **No-audio principle:** audio is scored in memory and discarded; only
  verdicts and transcripts persist — minimises the data-privacy/breach surface.
- **A/B-gated model changes:** no model swap ships without passing the
  channel-robust harness against the currently deployed model — this is what
  caught the ported public checkpoint underperforming (§8) before it could ship
  as a regression disguised as an upgrade.
- **Minimalism (intentional):** code is kept to the simplest version that
  works, with explicit `ponytail:` comments naming each deliberate shortcut and
  its upgrade path — so reviewers can see intent, not omission.

---

## 13. Honest limitations & future work

1. **Telephony/replay robustness is the known, prioritized gap** — the
   channel-augmented retrain (§8) is scoped and ready to run, just not yet run
   on GPU.
2. **Voiceprint/campaign threshold** needs calibration on real bank traffic —
   current values are reasonable defaults, not tuned operating points.
3. **Novelty** is a softmax-uncertainty heuristic → upgrade path is embedding-OOD.
4. **Campaign store** is a linear scan → FAISS/pgvector at scale.
5. **LLM is a cloud call** (NIM); on-prem deployment runs the same Nemotron as a
   self-hosted NIM container — code only changes a base URL.
6. **Speaker identity** (is it *this customer*?) is not yet built — anti-spoofing
   only; customer-voiceprint verification is the planned next layer.
7. **Adversarial robustness** (evasion via perturbation) is untested.

---

## 14. Tech stack

FastAPI · Uvicorn · PyTorch · torchaudio · librosa · transformers (wav2vec2) ·
faster-whisper (CTranslate2) · NVIDIA NIM (Nemotron) · aiortc-free WebRTC
signaling (media stays peer-to-peer in-browser) · scipy · scikit-learn · sqlite ·
Prometheus exposition · Vite + React (TanStack) + Tailwind · Docker.

> Summary: a layered, fail-safe pipeline where two independent neural detectors
> carry the verdict, an LLM adds human-scam coverage, an input-quality gate
> refuses to guess on bad audio, and rule-based fusion turns scores into
> auditable decisions — every accuracy number in this document is reproducible,
> and the roadmap above is exactly where the honest gaps are.
