# Dhwani-Kavach — Finals Deck Brief (everything you need to build the PPT)

**For:** the teammate building the finals presentation. This is the single source
of truth — the story, every feature, the numbers, the structure, and where the
detailed docs & diagrams live in the repo. Pull content straight from here into slides.

**Team:** ERROR 404 · **Product:** Dhwani-Kavach — a real-time call-fraud shield for banks.

---

## 0. Assets already in the repo (don't rebuild — reuse)

| File | What it is |
|---|---|
| `presentation.html` | **26-slide deck** (browser, keyboard-nav, print-to-PDF). Start here. |
| `tools/build_pptx.py` | Regenerates the editable **.pptx** (with speaker notes). Run `python tools/build_pptx.py` (close PowerPoint first). |
| `PRESENTATION-SCRIPT.md` | **40-min slide-by-slide speaking script + Q&A prep.** |
| `architecture.html` | Static **component/dataflow** diagram (screenshot into a slide). |
| `orchestration.html` | **Runtime control-flow** diagram (event loop, threads, background LLM). |
| `PRODUCT-EXPLAINER.md` | Plain-language walkthrough of every feature (bank-IT audience). |
| `TECHNICAL-OVERVIEW.md` | Deep technical description (academic/viva audience). |
| `COMPETITIVE-EDGE.md` | Where competitors lose + feature strategy. |
| `INTEGRATION.md` | How it plugs into a bank (SIPREC, API, deployment). |
| `DEMO-SCRIPT.md` | Live-demo runbook (the 6 beats). |
| `LEAVE-BEHIND.md` | One-page summary. |
| `ROADMAP-SHIELD.md` / `ROADMAP-EDGE.md` / `PHASE-H-KAGGLE.md` | Build plans / training runbook. |

> The `.pptx` and the 360 MB model are **not** in git. You have the model (sent
> separately) — drop it at `backend/models/deepfake_w2v.pt`. Regenerate the .pptx
> with the builder.

---

## 1. The 60-second story

Fraudsters clone a customer's or a relationship-manager's voice, or run scripted
human scams, to push transfers over the phone. **OTP and voice biometrics don't
stop a convincing clone or a coerced genuine customer.** Dhwani-Kavach listens to
the live call and, in ~4 seconds, returns one decision — **Monitor, Challenge, or
Block** — catching **both** AI voice clones **and** human scam scripts, on the
bank's own network, storing **no audio**.

Three words to anchor the whole talk: **live · on-prem · decision** (not "score").

**The reframe (say it early):** we didn't build a deepfake *detector* — that's a
commodity and it's narrow. We built a **fraud shield**. Our edge is everything a
detector isn't: the decision, the deployment, and the intelligence around it.

---

## 2. The problem (facts for the problem slide)

- Voice cloning is trivial — seconds of audio → a convincing clone.
- **Most vishing needs no deepfake at all** — a real human scammer coerces a real
  customer. This is the *larger* share of losses and the thing deepfake-only tools miss.
- The money moves **during** the call → post-call detection is worthless.
- Millions of calls, Hindi/English/code-mixed → humans can't screen them.
- Why current defenses fail: OTP is read out under pressure; biometrics are fooled
  by a clone and can't judge a coerced caller; agents can't hear a deepfake.

---

## 3. Every feature — what it is, how it works, the number, the "so what"

### A · Voice deepfake engine (the core)
- **What:** decides if the voice is AI-generated.
- **How:** 5-layer weighted ensemble. **wav2vec2 (self-supervised) neural model
  leads (weight 0.80)**; four handcrafted heuristics support: spectral/MFCC (0.07),
  breath (0.03), phase coherence (0.05), liveness (0.05). Score 0–100.
  **Bands: GREEN <40 · AMBER 40–69 · RED ≥70.** Worst 4-second window drives the
  verdict; silence is gated out.
- **Number:** ~**4% EER clean / 6% on phone lines** on modern fakes.
- **So what:** the actual anti-clone defense OTP/biometrics lack — and tuned on
  Indian voices so it doesn't false-flag real customers.

### B · Scam-script layer (human scammers)
- **What:** flags the *manipulation* even when the voice is a real human.
- **How:** rolling audio → **Whisper** speech-to-text → **NVIDIA Nemotron LLM** →
  scam score + tactics. **Six tactics:** urgency, authority impersonation, isolation,
  new-beneficiary, OTP/PIN request, threat. Runs in the background every ~4s.
- **Number:** verified — a Hindi scam scores **90/100** with correct tactics.
- **So what:** catches the majority of vishing that deepfake-only products miss.

### C · Decision fusion + transaction context
- **What:** turns scores into an action.
- **How (the rule):** `threat = voice≥70 OR scam≥70 OR novelty≥0.6`;
  `high_value = new payee OR amount ≥ ₹50,000`. → **BLOCK** if threat & high-value,
  **CHALLENGE** if threat, else **MONITOR**. Each with a plain-English reason.
- **So what:** proportionate, auditable decisions — a suspicious voice on a balance
  check ≠ on a ₹5-lakh transfer to a new payee.

### D · Novelty / zero-day
- **What:** flags a synthesis signature never seen.
- **How:** model uncertainty, `novelty = 1 − |2p − 1|`; ≥0.6 lifts GREEN → AMBER.
- **So what:** catches the clone tool that doesn't exist yet. (Honest: a heuristic;
  embedding-distance OOD is the upgrade.)

### E · Campaign / repeat-attacker detection
- **What:** links calls from the same synthetic voice.
- **How:** each call gets a **768-d voiceprint** (same forward pass, free); cosine
  match (threshold **0.85**); same voice across calls = a campaign; a prior-fraud
  voiceprint is **blocklisted** on its next call. Stored in sqlite.
- **So what:** "the same synthetic voice hit 14 customers" — fraud-ring intelligence
  that **compounds with use** (a data network effect competitors can't replicate).

### F · Telephony robustness
- **What:** works on real phone lines, not just clean mics.
- **How:** training audio degraded to **8 kHz, G.711 µ-law, band-limited, lossy** so
  the model learns telephony.
- **Number:** clean 4% vs phone **6% EER** — a ~2-point gap where un-augmented models
  show a cliff. Proven: a clone through an 8 kHz phone filter still reads RED.

### G · Multilingual
- Whisper auto-detects language; the LLM reasons in Hindi & Hinglish; the acoustic
  model is language-agnostic. Built for Indian customers.

### H · Shadow mode
- Score & log every call, **take no action**, for 30 days; measure detection &
  false-alarm rates on the bank's own traffic; then flip **one switch** to enforce.
  This is how banks safely adopt AI.

### I · Audit trail & forensic evidence packs
- Append-only record per call (stable `call_id`), **no audio** — transcript, tactics,
  layers, decision. Any flagged call opens as an evidence pack for disputes/regulators.

### J · Model governance
- Analyst labels → live **TPR/FPR**, **drift** alerts, **champion/challenger registry**
  — RBI Model Risk Management, built in.

### K · Metrics
- Prometheus endpoint (latency, verdict mix, errors) — scrapes into the bank's monitoring.

---

## 4. Numbers cheat-sheet (put these on slides)

| Metric | Value |
|---|---|
| First verdict latency | ~4 s (live), streaming update ~every 2 s |
| Deployed model EER | **4% clean / 6% phone-line** (modern fakes) |
| ASVspoof dev EER | 0.13% |
| Detection layers | 5 + LLM scam layer |
| Neural model weight | 0.80 (of the ensemble) |
| Scam tactics detected | 6 |
| Voiceprint dim / match threshold | 768-d / 0.85 cosine |
| Risk bands | GREEN <40 · AMBER 40–69 · RED ≥70 |
| Audio stored | 0 (verdict + transcript only) |
| TRL | 5 → 6 |

**Training journey (great for the technical panel):**
CNN 2.75% dev *(but 9.75% unseen → overfit)* → wav2vec2 0.40% *(false-flagged real
voices)* → +real Hindi 0.13% → +modern fakes ~5.2% → **+telephony 4%/6% (deployed)**.
*Honest caveat: these EERs are on different dev sets — not directly comparable; a single
fixed benchmark is future work.*

---

## 5. Architecture & orchestration (two slides)

- **Architecture (static):** Ingestion (live SIPREC→WebSocket 4s/2s · REST upload) →
  Detection engine (voice ensemble · scam-script · novelty · voiceprint) → Fusion +
  txn context → Outputs (agent/fraud engine · audit/evidence · campaigns · governance ·
  metrics). *Screenshot `architecture.html`.*
- **Orchestration (runtime):** one async **event loop** orchestrates; CPU inference
  runs **off-thread**; the heavy STT+LLM runs in a **throttled background task**; only
  the newest window is scored (backpressure); peak-hold decay for stability; every
  layer **fail-safe** (degrades to neutral). *Screenshot `orchestration.html`.*

---

## 6. Uniqueness & benchmark table (comparison slide)

**What only we do:** human-scam detection · works on real phone lines · fraud-campaign
intelligence · on-prem no-audio · zero-day novelty · multilingual.

| Capability | Academic (AASIST/RawNet2) | Commercial cloud | **Dhwani-Kavach** |
|---|---|---|---|
| ASVspoof dev EER | ~1% | n/a | **0.13%** |
| Modern / in-the-wild fakes | degrades (20–40%) | good | **~4–6% EER** |
| Telephony (8 kHz) | usually untested | varies | **6% EER (trained for it)** |
| Human scam (no deepfake) | ✗ | ✗ | **✓ LLM layer** |
| Deployment | research code | cloud API | **on-prem Docker** |
| Explainability & governance | ✗ | limited | **✓ built-in** |
| Campaign / fraud-ring intel | ✗ | some | **✓** |

**The honest framing:** academic SOTA beats us on the ASVspoof leaderboard but
generalises poorly cross-dataset. **Accuracy is table-stakes; we optimise for the
real deployment, not the leaderboard.**

**Technical moat:** data network effect (blocklist smarter with use) · generator-diverse
training · prompt-adaptable scam layer · novelty self-guarding · governance-as-moat ·
on-prem trust under RBI localisation.

---

## 7. Deployability, integration, trust

- **On-prem Docker** in the bank DMZ; **no audio leaves the bank** (RBI-clean);
  stateless, scales horizontally, CPU-viable; API-key/mTLS, TLS, audit trail.
- **Integration:** SIPREC/media-fork from existing telephony (Genesys/Avaya/Cisco) →
  our WS/REST API → agent screen or fraud engine. **No rip-and-replace.** Three
  plug-in points: contact-centre (primary), anti-spoof in front of voice biometrics,
  batch dispute review. Same JSON verdict everywhere.

---

## 8. TRL, roadmap, timeline (demo-section slides)

- **TRL 5 → 6:** working prototype, validated on realistic data (ASVspoof + real
  Indian voices + modern fakes + telephony), deployable Docker + governance.
  **Path to 7–8:** 30-day shadow pilot on a bank queue → calibrate on real traffic →
  harden SIPREC + mTLS.
- **Done:** core shield (5-layer + scam LLM + fusion + novelty + audit); edge phases
  (shadow, multilingual, evidence packs, campaigns, governance); telephony retrain deployed.
- **Next:** customer voice-identity + liveness; embedding-based novelty; broader
  generator diversity. **Then:** bank PoC.

---

## 9. Honest limitations (the "viva armor" slide — say it with confidence)

1. Thresholds (voiceprint 0.85, fusion cut-offs, ensemble weights) are **hand-set
   defaults**, not ablated → calibrate on real traffic in a pilot.
2. Novelty is a softmax-uncertainty **heuristic** → embedding-distance OOD is the upgrade.
3. Campaign store is a **linear scan** → FAISS/pgvector at scale.
4. EERs on **differing dev sets** → one fixed benchmark with CIs next.
5. LLM is a **cloud call** → same Nemotron as an on-prem NIM container (base-URL change).
6. **Customer voice-identity** (is it *this* customer?) not built yet — anti-spoofing only.
7. **Adversarial-evasion** robustness untested.

*Why the heuristics (e.g. phase) are low-weight:* they're cheap, interpretable,
training-free signals that catch specific synthesis artifacts (phase = vocoders have
over-regular phase), giving ensemble diversity — but modern vocoders have closed much of
that gap, so they're individually weak; the neural model carries the verdict.

---

## 10. Suggested finals slide outline (adapt to the time slot)

1. Title (Team ERROR 404) · 2. Agenda · 3. Problem · 4. Two attack vectors ·
5. The insight (fraud shield) · 6. Solution overview · 7. Architecture · 8. Orchestration ·
9. Deep-dive: detection layers · 10. Model & training journey · 11. Scam-script + multilingual ·
12. Decision fusion · 13. Novelty + campaigns · 14. Telephony · 15. Uniqueness ·
16. Benchmarks · 17. Technical moat · 18. Engineering rigor · 19. Deployability ·
20. Governance & trust · 21. Honest limitations · 22. Demo · 23. TRL · 24. Roadmap ·
25. Integration · 26. Impact · 27. Q&A.

*(This mirrors `presentation.html`. Trim/merge to fit the finals time limit.)*

---

## 11. Brand / design (so the deck looks consistent)

- Dark background `#0B0E14` / panels `#0F1117`; accent **cyan `#5EEAD4`**;
  GREEN `#22C55E`, AMBER `#F59E0B`, RED `#FF4D6D`; text `#F1F5F9`, muted `#8A96A8`.
- Monospace for data/labels, sans for body. One idea per slide. Keep the three
  green/amber/red bands visible — it's the product's visual signature.

## 12. Q&A prep
See the **Q&A section in `PRESENTATION-SCRIPT.md`** — the 12 hardest questions
(overfitting, false-positive rate, why rule-based fusion, cloud LLM vs on-prem,
adversarial, why trust a student prototype…) with crisp, honest answers.

## 13. Run it locally (to grab live screenshots for the deck)
```bash
pip install -r backend/requirements.txt
pip install faster-whisper           # optional: scam-script STT
cd frontend && npm install
# place deepfake_w2v.pt in backend/models/ ; set NVIDIA_API_KEY
```
Then `start-demo.bat` → dashboard at http://localhost:8080; backend pages at
http://localhost:8000/cases · /campaigns · /governance · /metrics.
