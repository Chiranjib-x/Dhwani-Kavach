# Dhwani-Kavach — Technical Overview (for academic review)

A complete, honest technical description: architecture, algorithms, models,
training, evaluation, engineering decisions, and limitations. Written for a
technical panel that needs to understand *how* and *why* each part works.

---

## 1. System architecture

A FastAPI service exposing two ingestion paths into one shared detection engine:

```
                          ┌──────────────── Detection engine ────────────────┐
 REST  POST /api/analyze ─┤  audio → [5-layer voice ensemble]                │
 (files, disputes)        │          [scam-script: STT → LLM]                │
                          │          [novelty]   [voiceprint/campaign]       │
 WS  /ws/analyze ─────────┤              │                                   │
 (live, 4s/2s windows)    │       [decision fusion + txn context]            │
                          └──────────────┬───────────────────────────────────┘
                                         ▼
                       {risk_score, alert_level, action, layer_breakdown,
                        scam, novelty, campaign, mode, call_id}
                                         │
                 audit log (JSONL) · metrics (Prometheus) · governance · campaigns
```

- **Backend:** FastAPI + Uvicorn, PyTorch, torchaudio/librosa, transformers.
- **Frontend:** Vite + React (live dashboard + file-upload UI).
- **Design principle:** every advanced layer is **additive and fail-safe** — if a
  dependency (STT, LLM, model file) is missing, that layer returns neutral and the
  rest of the pipeline still produces a verdict.

---

## 2. Voice deepfake detection — the core ensemble

Five layers produce per-window spoof probabilities in [0,1]; a weighted ensemble
gives a 0–100 risk score, banded **GREEN <40 / AMBER 40–69 / RED ≥70**.

**Ensemble weights** (the trained model leads; heuristics are minor support):

| Layer | Weight | Method |
|---|---|---|
| `aasist` (neural) | 0.80 | wav2vec2 SSL classifier (below) |
| `mfcc` | 0.07 | handcrafted spectral/MFCC features |
| `breath` | 0.03 | breath-pattern energy heuristic |
| `phase` | 0.05 | phase-coherence analysis |
| `liveness` | 0.05 | liveness/articulation heuristic |

**Aggregation over a whole recording:** audio is split into 4 s chunks; the
**worst (highest-risk) chunk drives the verdict** — semantically, *a deepfake
anywhere in the call is a deepfake*. Near-silent chunks (RMS < 1e-3) are gated out
to avoid scoring noise. Chunks are capped (strided) so long calls stay bounded in
latency.

### 2.1 The neural detector (wav2vec2 SSL)
- **Architecture:** `wav2vec2-base` (self-supervised speech encoder, feature
  encoder frozen) → mean-pool over time (768-d) → MLP head
  `Linear(768,256) → ReLU → Dropout(0.3) → Linear(256,2)` → softmax; spoof = P(class 1).
- **Preprocessing (must match training):** 16 kHz mono, zero-pad/trim to 4 s
  (64 000 samples), **per-utterance standardisation** `(x−μ)/(σ+ε)`.
- **Why SSL:** wav2vec2 is pretrained on large unlabelled speech; fine-tuning a
  light head on top generalises far better than a from-scratch CNN, especially to
  unseen attacks and real-world recording conditions.

### 2.2 Why not just the CNN?
A mel-spectrogram CNN was the first baseline (kept as a fallback). It reached
2.75% DEV EER but **9.75% on unseen attacks** and false-flagged real laptop-mic
voices — a domain-generalisation gap. The SSL model closed both. The CNN remains
as a graceful fallback if the SSL weights are absent.

---

## 3. Training & evaluation

**Metric:** Equal Error Rate (EER) — the operating point where false-accept =
false-reject rate; standard for anti-spoofing, lower is better.

**Data + result progression** (each step fixed a concrete failure):

| Stage | Training data | DEV EER | Note |
|---|---|---|---|
| CNN baseline | ASVspoof 2019 LA | 2.75% | unseen-attack EER 9.75% |
| SSL v1 | ASVspoof LA + noise/gain aug | 0.40% | narrow "real" → false-flags real voices |
| SSL v2 | + Common Voice **Hindi** (real) | 0.13% | broadened "real"; clones still slipped |
| SSL v3 (modern) | + In-the-Wild, Fake-or-Real, **user clones** | ~5.2% (modern fakes) | realistic, harder eval set |
| SSL v4 (telephony) | + **telephony augmentation** | **clean 4.0% / phone 6.0%** | deployed |

**Telephony augmentation:** clean audio is degraded to phone-line quality —
300–3400 Hz band-limit, resample to 8 kHz, **G.711 µ-law** companding, optional
20 ms packet-loss — applied to ~50% of training clips. Result: the clean→phone EER
gap is only ~2 points (an un-augmented model shows a large cliff). This is the
"works on real lines" claim, quantified.

**Honest note on EER comparability:** the EERs above are on *different* dev sets
(ASVspoof dev vs Fake-or-Real validation), so they are not directly comparable
across rows — each measures progress against the failure that motivated that step,
not a single fixed benchmark.

---

## 4. Streaming engine (live calls)

- **Windowing:** raw 16 kHz float32 PCM frames are buffered into **4 s windows with
  a 2 s hop** (50% overlap) → a fresh verdict ~every 2 s; first verdict ~4 s in.
- **Off-thread inference:** CPU-bound torch runs via `asyncio.to_thread` so the
  event loop (and other connections) aren't blocked.
- **Backpressure:** only the **newest** window is scored; backlog is discarded.
  Without this, a slow CPU lets windows queue and then floods the client — the
  cause of an early UI freeze.
- **Peak-hold with decay:** a single 4 s window can be noisy. The displayed risk is
  `peak ← max(risk, peak·0.9)` per window, so a detected spike (e.g. a clone
  flagged in one window) **stays flagged for several seconds then decays**, rather
  than vanishing the next window — matching the file path's worst-chunk semantics,
  while still recovering for the next speaker (no cross-call carryover).

---

## 5. Scam-script detection (human scammers)

- **Pipeline:** rolling audio → **Whisper** (`faster-whisper`, base, int8 CPU) →
  transcript → **LLM** (NVIDIA Nemotron via the NIM OpenAI-compatible API) →
  `{scam_score, tactics}`.
- **Tactics** (closed set, evidence-required prompt): urgency, authority
  impersonation, isolation, new-beneficiary, sensitive-info (OTP/PIN) request, threat.
- **Throttling:** STT+LLM is heavier, so it runs **in the background every ~4 s**
  over the last ~8 s of audio and is folded into the next verdict — it never blocks
  the 2 s detection cadence.
- **Multilingual:** Whisper auto-detects language; the LLM reasons in Hindi/Hinglish.
- **Fail-safe:** no key / no STT / network error → neutral score; voice detection unaffected.

---

## 6. Decision fusion

Rule-based (deliberately, for auditability — every decision is explainable):

```
threat   = voice_risk≥70  OR  scam_score≥70  OR  novelty≥0.6
high_value = new_beneficiary OR amount ≥ ₹50,000
action = BLOCK     if threat and high_value
         CHALLENGE if threat
         MONITOR   otherwise
```
Each action carries a plain-English reason. Thresholds are tunable per the bank's
risk appetite. (Rationale: a learned policy needs labelled outcome data the system
must first accumulate; the rule layer is the honest v1 and the fallback.)

---

## 7. Novelty / zero-day detection

- **Signal:** the neural model's own uncertainty. With spoof prob `p`,
  `novelty = 1 − |2p − 1|` (peaks at p=0.5). High novelty = the input looks unlike
  confident-real or confident-fake → an unfamiliar synthesis signature.
- **Action:** novelty ≥ 0.6 lifts a GREEN verdict to AMBER.
- **Honest limitation:** this is a **softmax-uncertainty heuristic, not true
  out-of-distribution detection.** A calibrated upgrade is embedding-distance OOD
  (Mahalanobis to class centroids) — noted as the upgrade path in code.

---

## 8. Campaign / repeat-attacker detection

- **Voiceprint:** the mean-pooled wav2vec2 embedding (768-d, **L2-normalised**),
  obtained from the *same* forward pass as detection (no extra cost).
- **Correlation:** cosine similarity (= dot product of normalised vectors) against
  stored voiceprints (sqlite). Match ≥ **0.85** → same cluster (campaign); a
  voiceprint from a previously-flagged call hits a **blocklist** on its next call.
- **Honest limitations:** (a) wav2vec2 mean-pool is **not** a dedicated
  speaker-verification space, so the 0.85 threshold must be **calibrated on real
  clones** in a pilot; (b) it's a **linear scan** — fine for a branch/PoC, needs
  FAISS/pgvector beyond ~100k voiceprints.

---

## 9. Governance, audit, observability

- **Audit log:** append-only JSONL, one line per verdict, stable `call_id`,
  **no audio** (transcript text only). Backs the forensic evidence packs.
- **Confusion matrix:** analyst fraud/legit labels are joined to audit verdicts →
  live **TPR / FPR / precision**.
- **Drift:** two-window heuristic — flagged-rate in the recent window vs the
  baseline; |Δ| ≥ 0.2 raises an alert. (Upgrade path: PSI / proper time-series.)
- **Model registry:** champion/challenger with version, training data, eval scores.
- **Metrics:** Prometheus exposition (latency, verdict mix, errors).
- **Shadow vs enforce:** a policy flag — score+log only, or act — for risk-free piloting.

---

## 10. Notable engineering decisions

- **Fail-safe composition:** advanced layers degrade to neutral; the core verdict
  always survives a missing dependency.
- **OpenMP conflict:** torch and ctranslate2 (Whisper) each ship an Intel OpenMP
  runtime; on Windows both load `libiomp5md.dll` and the duplicate-init check aborts
  the process. Resolved with `KMP_DUPLICATE_LIB_OK` set before import (same runtime,
  safe) — the clean alternative is isolating STT in a subprocess.
- **No-audio principle:** audio is scored in memory and discarded; only verdicts
  and transcripts persist — minimises the data-privacy/breach surface.
- **Minimalism (intentional):** code is kept to the simplest version that works,
  with explicit `ponytail:` comments naming each deliberate shortcut and its
  upgrade path — so reviewers can see intent, not omission.

---

## 11. Honest limitations & future work

1. **Threshold calibration** (voiceprint 0.85, fusion cut-offs) needs real bank
   data — current values are reasonable defaults, not tuned operating points.
2. **Novelty** is a softmax-uncertainty heuristic → upgrade to embedding-OOD.
3. **Campaign store** is a linear scan → FAISS/pgvector at scale.
4. **EERs** are reported on differing dev sets; a single fixed, telephony-inclusive
   benchmark with confidence intervals is the next evaluation step.
5. **LLM is a cloud call** (NIM); on-prem deployment runs the same Nemotron as a
   self-hosted NIM container — code only changes a base URL.
6. **Speaker identity** (is it *this customer*?) is not yet built — anti-spoofing
   only; customer-voiceprint verification is the planned next layer.
7. **Adversarial robustness** (evasion via perturbation) is untested.

---

## 12. Tech stack

FastAPI · Uvicorn · PyTorch · torchaudio · librosa · transformers (wav2vec2) ·
faster-whisper (CTranslate2) · NVIDIA NIM (Nemotron) · scipy · scikit-learn ·
sqlite · Prometheus exposition · Vite + React + Tailwind · Docker.

> Summary: a layered, fail-safe pipeline where a fine-tuned SSL model carries the
> verdict, an LLM adds human-scam coverage, and rule-based fusion turns scores into
> auditable decisions — engineered to run on-prem, in real time, with the honest
> limitations above as the roadmap.
