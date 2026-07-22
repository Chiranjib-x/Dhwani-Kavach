# Dhwani-Kavach — Product & Integration Guide for Bank IT

A precise, plain-language walkthrough of the entire system: what each part does,
how it works, how it plugs into your environment, and why it matters. Written
for your IT and fraud teams.

---

## 1. What it is, in one paragraph

Dhwani-Kavach is a **real-time call-fraud shield**. It listens to a banking call,
and within seconds returns a single decision — **Monitor, Challenge, or
Block** — backed by a 0–100 risk score and an explainable breakdown. It catches
**AI voice clones (deepfakes)** *and* **human social-engineering scams**, runs
**inside the bank's own network**, and stores **no audio**. When the call audio
itself is too degraded to judge (bad mic, noisy line), it says so — **Uncertain**
— instead of guessing. It is not a research model; it is a deployable service
with auditing, governance, and monitoring built in.

**The problem it solves:** fraudsters now clone a customer's or relationship
manager's voice, or pressure customers with scripted scams, to authorise
transfers. OTP and existing voice biometrics do **not** stop a convincing clone
or a coerced-but-genuine customer. Dhwani-Kavach is the missing layer.

---

## 2. How a call flows through it (end to end)

```
 Live call audio ──► [1] Voice deepfake check (2 independent neural detectors
                          + input-quality gate)
                     [2] Scam-script check (speech-to-text → LLM → tactics)
                     [3] Novelty check (unknown synthesis signature)
                     [4] Voiceprint check (seen this voice before? campaign?)
                            │
                            ▼
                     [5] Decision fusion  +  transaction context
                            │
                            ▼
              MONITOR / CHALLENGE / BLOCK  (+ score, + reasons, or UNCERTAIN)
                            │
                ┌───────────┼───────────────┐
                ▼           ▼                ▼
           Agent screen  Audit log     Metrics / Governance
           / fraud engine (evidence)   (TPR/FPR, drift)
```

Two ways calls come in: **live streaming** (WebSocket, for in-progress calls) and
**file upload** (REST, for recordings/disputes). Both run the same engine and
return the same verdict shape.

---

## 3. Each functionality, explained

### A. Voice deepfake detection (the core)
- **What:** decides if the *voice itself* is AI-generated.
- **How:** **two independent neural detectors** — different architectures,
  different training data, so their blind spots don't overlap — vote 50/50.
  One is a codec/compression-artifact specialist; the other is fine-tuned
  specifically on modern commercial voice-clone engines (ElevenLabs and
  similar). Four supporting acoustic checks (spectral biometrics, breath
  patterns, phase coherence, liveness) are shown as evidence for the analyst
  but don't vote — they were measured not to reliably separate real from fake,
  and letting them vote diluted confident verdicts. A 0–100 score is banded
  **GREEN (<~52) / AMBER / RED (~67+)**, calibrated on labeled real/clone audio.
- **Accuracy:** clean-audio calibration currently separates real and clone
  scores cleanly on our labeled set (0% error, real scores capping well below
  fake scores). Telephony/channel robustness is the actively-tracked gap — a
  targeted retrain is queued and we report the honest number, not the best-case
  one (see TECHNICAL-OVERVIEW.md §3 for the full methodology).
- **Why the bank cares:** this is the actual anti-clone defence OTP/biometrics
  lack — and it's built to be transparent about where it's strong vs. where it
  still needs work, which is exactly what a model-risk team wants to see.

### B. Input-quality gate — "we don't guess on a bad line"
- **What:** before trusting a verdict, checks whether the audio itself (level,
  clipping, background noise) is even good enough to judge.
- **How:** if the input is too quiet, clipping, or buried in noise, the verdict
  is **UNCERTAIN** with a plain-language reason ("move to a quieter place"),
  and the system steps up authentication rather than either clearing the call
  or falsely alarming on it.
- **Why the bank cares:** a system that confidently flags genuine customers on
  a bad connection is worse than useless — it destroys agent trust and floods
  the fraud desk. This is the honest alternative: know what you don't know.

### C. Scam-script detection (human scammers, no deepfake)
- **What:** flags the *manipulation*, even when the voice is a real human.
- **How:** the call is transcribed (speech-to-text) and read by an LLM that scores
  scam likelihood and tags tactics — **urgency, authority impersonation, isolation
  ("don't tell anyone"), new-beneficiary pressure, OTP/PIN requests, threats**.
- **Why the bank cares:** **most vishing uses a real human, not a deepfake.** A
  deepfake-only product scores those calls safe. This closes that gap — arguably
  the bigger share of real fraud.

### D. Decision fusion + transaction context
- **What:** turns scores into an **action** the fraud engine can take.
- **How:** combines voice risk + scam risk + novelty + input quality + the
  transaction being requested (amount, new payee) into **MONITOR / CHALLENGE /
  BLOCK**, each with a plain-English reason (e.g. *"synthetic-voice risk 82
  during a new payee transfer"*).
- **Why the bank cares:** a balance enquiry with a suspicious voice is low-stakes;
  a ₹5-lakh transfer to a new payee is a code-red. Context makes the response
  proportionate — and gives your fraud engine a decision, not just a number.

### E. Novelty / zero-day detection
- **What:** flags a synthesis signature it has **never seen before**.
- **How:** measures the neural detectors' own uncertainty (and disagreement
  between the two of them); an "unknown" pattern lifts a GREEN verdict to AMBER
  instead of passing clean.
- **Why the bank cares:** a new voice-clone tool ships every month. This catches
  the clone tool that **doesn't exist yet**, so the product doesn't go stale.

### F. Campaign / repeat-attacker detection
- **What:** links calls made by the **same** synthetic voice.
- **How:** each call gets a **voiceprint** (a numeric fingerprint). New calls are
  matched against past ones; the same voice across many calls forms a **campaign**,
  and a voiceprint that already committed fraud is flagged on its next call (blocklist).
- **Why the bank cares:** moves you from "one suspicious call" to *"this same voice
  hit 14 of your customers today"* — fraud-ring intelligence. It also **improves
  with use**: the more calls, the smarter the blocklist.

### G. Telephony robustness — where we're honest, not oversold
- **What:** works on real phone lines, not just clean studio audio.
- **How:** the model is evaluated on 8 kHz/G.711-degraded audio, and a
  channel-augmented retrain (real room impulse responses, telephony,
  reverb, noise) is queued specifically to close this gap.
- **Why the bank cares:** most detectors are demoed on a laptop mic and fail on
  the bank's actual lines. We measure this honestly and tell you exactly where
  we stand today rather than hiding behind a best-case demo number.

### H. Multilingual (Hindi / Hinglish / regional)
- **What:** detects scams in Indian languages and code-mixed speech.
- **How:** speech-to-text auto-detects the language; the deepfake model is
  language-agnostic (it reads acoustics, not words).
- **Why the bank cares:** your customers don't call in clean English. Western,
  English-only tools miss this.

### I. Shadow mode vs Enforce mode
- **What:** a switch between "watch and log only" and "act on verdicts."
- **How:** in **shadow**, every call is scored and logged but **no action** is
  taken; in **enforce**, RED verdicts trigger step-up auth / blocking. Toggle by
  config, API, or a dashboard switch.
- **Why the bank cares:** you pilot risk-free — run it in shadow on your own
  traffic for 30 days, compare to reality, then flip to enforce when the numbers
  prove out. This is how banks safely adopt anything new.

### J. Audit trail & forensic evidence packs
- **What:** a permanent, searchable record of every verdict — **with no audio**.
- **How:** each call gets a stable ID and an append-only log entry (score, level,
  tactics, language, transcript, decision). Any flagged call opens as an **evidence
  pack** for disputes, FIRs, or regulators.
- **Why the bank cares:** you can't act on fraud you can't defend in an audit. This
  is the defensible paper trail — and storing no audio minimises data-privacy risk.

### K. Model governance dashboard
- **What:** lets your model-risk team **govern** the AI.
- **How:** analysts label flagged calls (fraud/legit); the system computes live
  **detection rate (TPR)** and **false-alarm rate (FPR)**, watches for **drift**
  (the verdict pattern shifting over time), and keeps a **model registry**
  (version, training data, eval scores, champion vs challenger).
- **Why the bank cares:** **RBI Model Risk Management** requires you to monitor and
  govern any model in production. This is built in — most vendors make you build it.

### L. Metrics / observability
- **What:** operational health for your monitoring team.
- **How:** a standard **Prometheus** endpoint exposes latency, verdict mix, and
  error rate; scrapes straight into your existing dashboards.
- **Why the bank cares:** it runs like any other production service you already operate.

---

## 4. Where it fits in the bank environment

Three integration points, in order of impact:

### A. Contact centre / IVR — live fraud screening (primary)
Your telephony platform (Genesys / Avaya / Cisco) already has the call audio.
A **media fork / SIPREC connector** copies the caller's audio leg to a small
adapter, which streams raw PCM to `ws /ws/analyze`. The verdict surfaces:
- on the **agent's screen** as a live risk badge, and/or
- as a **signal into your fraud-decisioning engine** to auto-trigger step-up
  auth (OTP, security questions) when the score hits RED.

```
Caller ──► Telephony (Genesys/Avaya) ──► SIPREC/media fork ──► Adapter
                                                                  │ PCM 16k
                                                                  ▼
                                                       Dhwani-Kavach  (on-prem)
                                                                  │ JSON verdict
                                                                  ▼
                                              Agent dashboard  /  Fraud engine
```

The demo build ships an equivalent path over **WebRTC** (`/call`, two roles:
Customer/Agent) so a live call can be shown end-to-end without any telephony
infrastructure — the agent side taps the incoming audio track digitally, the
same way a SIPREC adapter would, rather than a physical speaker-to-microphone
setup (which is a fundamentally harder detection problem — see
TECHNICAL-OVERVIEW.md §4).

### B. Voice-biometric authentication — anti-spoofing layer
If the bank uses (or plans) voice biometrics for phone-banking login,
Dhwani-Kavach runs **in front of it** as a presentation-attack / deepfake
check: biometric says "this is customer X's voice", Dhwani-Kavach says "and
it's a live human, not a clone". The two together close the spoofing gap that
voice biometrics alone have.

### C. Recorded-call / dispute review — batch
Investigations and dispute teams `POST` recorded calls to `/api/analyze` to
flag synthetic-voice fraud after the fact. Same engine, no live plumbing.

---

## 5. Deployment model

- **On-premise / private VPC.** Ships as a Docker container. Runs inside the
  bank DMZ or private cloud. Satisfies **RBI data-localisation** — call audio
  never touches the public internet or any third party.
- **Stateless & no audio retention.** Audio is scored in memory and discarded;
  only the verdict (score + level + layer breakdown) is returned. Nothing to
  breach, minimal data-privacy surface.
- **Horizontal scale.** Stateless service → run N replicas behind the bank's
  load balancer, sized to peak concurrent calls. CPU-only inference works;
  one GPU per node raises throughput if needed.
- **Footprint.** Single service + a ~306 MB model bundle. No external DB
  required for scoring (Redis optional, only for multi-node alert fan-out).
  Boots and scores with **zero external network dependency**.

## 6. What we harden for production (vs. the demo)

The demo build is deliberately open. For a bank deployment we add the standard
controls — all are small, known additions, not research:

| Area | Demo today | Production integration |
|------|-----------|------------------------|
| Auth | API-key on REST routes | + **mTLS** between adapter and service on the WS/telephony path; CORS locked to bank origins |
| Transport | plain HTTP/WS | TLS everywhere (bank PKI) |
| Audit | JSONL, in-process | Append-only verdict log ships to durable/hash-chained storage; **no audio stored** |
| Packaging | run from source | Hardened Docker image, health/readiness probes, resource limits |
| Observability | logs + `/metrics` | Prometheus metrics into the bank's monitoring stack |

None of these touch the detection engine — they wrap it.

---

## 7. Verdict contract (what the bank's systems consume)

`POST /api/analyze` and the live socket both return the same shape:

```json
{
  "risk_score": 82,
  "alert_level": "RED",
  "layer_breakdown": {
    "aasist": 86, "clone_v3": 91,
    "mfcc": 40, "breath": 75, "phase": 30, "liveness": 20
  },
  "quality": { "ok": true, "score": 92, "reason": "ok", "snr_db": 28.4 },
  "novelty": 0.12,
  "action": "CHALLENGE",
  "action_reason": "synthetic-voice risk 82 during a new payee transfer",
  "model_version": "w2v2aasist-cotrain+clone_v3",
  "call_id": "8e2990ddad0a"
}
```

- `risk_score` 0–100, `alert_level` GREEN/AMBER/RED/**UNCERTAIN**.
- `layer_breakdown` makes every verdict **explainable** — the neural detectors
  (`aasist`, `clone_v3`) drive the verdict; the rest are evidence-only.
- `quality` — when `ok:false`, the score should not be trusted; `alert_level`
  will read UNCERTAIN and `reason` explains why.
- Thresholds are tunable to the bank's risk appetite.

---

## 8. Security & compliance posture

- On-prem, **no audio leaves the bank**, no audio stored.
- **API-key auth + locked CORS** (production adds mTLS + TLS via your PKI).
- **Append-only audit trail** for every verdict.
- **Explainable** verdicts (per-layer + tactics + reason) — no black box.
- **Governable** (TPR/FPR, drift, versioning) for RBI Model Risk Management.

## 9. Suggested rollout

1. **PoC (weeks):** point a recorded-call sample set at `POST /api/analyze`,
   measure detection rate + false-positive rate on the bank's own audio.
2. **Pilot (live, one queue):** SIPREC fork on a single contact-centre queue →
   agent-screen badge, verdicts logged but not yet auto-acting (shadow mode).
3. **Production:** wire RED verdicts into the fraud-decisioning engine for
   automated step-up auth; scale replicas to full call volume.

> Tuning to the bank's own call audio in the PoC is expected and important —
> the false-positive threshold should be calibrated on real bank traffic, not
> just our test sets. We designed for exactly this: calibration is a one-command
> refit, not a retraining project.

## 10. Why it's worth it — the bottom line

1. Stops the fraud OTP/biometrics can't: **voice clones** *and* **human scams**.
2. **Real-time** — acts during the call, before money moves.
3. **On-prem, no audio retained** — RBI-aligned, low data risk.
4. **Honest about uncertainty** — abstains instead of guessing, and every
   accuracy claim is reproducible from the code, not a marketing number.
5. **Fraud-ring intelligence** that compounds with use.
6. **Audit-ready and governable** — deployable, not a science project.
7. **Pilots risk-free in shadow**, integrates without replacing your stack.

> In short: a deployable, explainable, on-prem layer that closes the voice-fraud
> gap — built for how your calls, customers, and regulators actually work.
