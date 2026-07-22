# Dhwani-Kavach — Competitive Edge & Feature Strategy

Deep analysis of what to add to beat teams shipping "the same product"
(deepfake-voice detection for banks). Framed around **where competitors lose a
bank deal**, not features in a vacuum.

---

## 1. The core thesis

A deepfake detector is a commodity — any team can fine-tune wav2vec2/AASIST on
ASVspoof. Competitors will all claim "high accuracy." You don't win on the
model. You win on the **four places every commodity detector quietly fails**,
because that's where a bank's procurement team kills the deal:

1. **It dies on a real phone line.** Demos run on a clean laptop mic at 16 kHz.
   Real bank calls are 8 kHz, G.711/AMR-codec, packet-loss telephony. Models
   trained on clean audio collapse on telephony. **This is the #1 production
   failure** and the first thing a serious bank will test. *(We measure this
   honestly — see §3 — rather than hiding it behind a best-case demo.)*
2. **It only catches deepfakes.** Most vishing is a *real human* scammer. A
   deepfake-only product scores the actual fraud GREEN. *(You already closed
   this with the scam-script LLM — keep hammering it.)*
3. **It can't be governed.** Banks have Model Risk Management duties (RBI / Basel).
   No FPR/TPR-over-time, no drift monitoring, no versioning = can't go to prod.
4. **It flags real customers.** A high false-positive rate on genuine callers is
   worse than useless — it destroys customer trust and floods the fraud desk.
   *(Our answer isn't just "low FPR" — it's the input-quality gate: when the
   line is too bad to trust, we say UNCERTAIN instead of guessing GREEN or RED.
   No competitor demo does this.)*

Build where they lose. The features below are ranked by **(deal impact) ×
(feasibility given what you already have)**.

---

## 2. Tiering — know what NOT to compete on

| Tier | Capability | Stance |
|------|-----------|--------|
| **Table stakes** | A deepfake classifier; an accuracy number | Don't lead here — everyone claims it |
| **Your current moat** | Scam-script LLM, on-prem, two independent neural detectors + explainable evidence signals, input-quality abstention, fused MONITOR/CHALLENGE/BLOCK, novelty/zero-day, audit trail, /cases, /metrics | Lead with these |
| **Next moat (this doc)** | Telephony-grade robustness, multilingual, campaign detection, governance, shadow-mode | Build these to be uncatchable |

---

## 3. The features that win — ranked

### #1 — Telephony-grade robustness  ★ highest deal impact, honestly in progress
**What:** channel-augmented fine-tuning (real room impulse responses, telephony
codec, reverb, noise) so the model that already carries the live verdict also
holds up off a clean mic.
**Where we actually stand:** we measure this rigorously, not optimistically —
current channel-robust evaluation shows clean-audio separation is strong while
telephony/reverb/replay are the honestly-tracked weak channels. The retrain to
close this gap is scoped and ready to run (warm-started from a stronger public
checkpoint we already ported and benchmarked — see §6). **This candor is itself
a selling point**: a team that shows you their weak channel with real numbers is
more credible than one that shows you a cherry-picked demo clip.
**Why it beats competitors:** their laptop-mic demo will *fail the bank's own
phone-line test*, and they likely haven't even measured it the way we have.
**Bank need:** non-negotiable — real calls are telephony.
**Effort:** medium (retrain warm-start + augmentation pipeline already built;
needs one GPU run).
**Demo angle:** show the channel-robustness eval table live — real numbers, not
a single lucky clip.

### #2 — Multilingual / Hinglish coverage  ★ near-free, India-specific
**What:** handle Hindi, English, code-mixed Hinglish, and major regional
languages on the scam-script layer.
**Why it beats competitors:** Western detectors and English-only NLP fail on
Indian banking calls. You largely **already have this** — Whisper auto-detects
language and Nemotron reasons in Hindi/English; the acoustic deepfake model is
language-agnostic. So this is mostly a *positioning + a Hinglish test set*, not
a big build.
**Bank need:** direct fit for the bank's actual customer base.
**Effort:** low (verify + a curated Hinglish/regional eval; surface detected
language in the UI).
**Demo angle:** run a Hindi/Hinglish scam call live → tactics still light up.

### #3 — Fraud-campaign & repeat-attacker detection  ★ compounding moat
**What:** fingerprint each call's voice embedding; cluster across calls to flag
"the *same* synthetic voice hit 14 customers today" and maintain a fraudster
voiceprint blocklist.
**Why it beats competitors:** this is a **data network effect** — the more the
bank uses it, the smarter it gets, and a competitor can't replicate the data.
Moves you from "per-call score" to "fraud-ring intelligence," which is what
fraud teams actually chase.
**Bank need:** campaign-level detection + blocklisting is high-value.
**Effort:** medium (the neural embeddings already exist — add storage +
nearest-neighbour clustering). **Already built.**
**Demo angle:** show two different "customer" calls flagged as the *same*
underlying synthetic voice.

### #4 — Model governance & drift dashboard  ★ procurement-winner
**What:** a dashboard of FPR/TPR over time, verdict drift, model version,
champion/challenger, and a per-model data sheet. `/metrics` + `/governance`.
**Why it beats competitors:** banks *cannot* deploy a model they can't govern
(RBI Model Risk Management). No hackathon team will have this. It signals
"production-grade vendor," not "student project."
**Bank need:** mandatory for go-live.
**Effort:** **already built.**
**Demo angle:** "here's how your model-risk team monitors us in production."

### #5 — Shadow-mode pilot capability  ★ how you actually land the deal
**What:** a mode that scores every live call and logs verdicts **without taking
action** — so the bank measures real detection + false-positive rates on their
own traffic before trusting it to act.
**Why it beats competitors:** it's the *sales motion* banks demand — prove value
risk-free first. Offering it shows you understand how banks buy.
**Bank need:** every bank pilots in shadow before enforcement.
**Effort:** **already built** (a config flag; the audit log already records everything).
**Demo angle:** "run us in shadow for 30 days, then turn on enforcement."

### #6 — "We test rigorously and tell you the truth" ★ new, underused
**What:** we ported the strongest public open-weights deepfake detector we
could find in the research literature, built a proper channel-robust A/B
harness, and tested it head-to-head against our own model — and it **lost** on
4 of 5 real-world channels, so we didn't ship it. It's now feeding our next
retrain instead.
**Why it beats competitors:** every team at a hackathon will claim their model
is "the best." Almost none will show you an experiment where they tried
something that looked better on paper and rejected it because their own testing
said so. This is the single strongest signal of engineering maturity you have,
and it costs nothing extra to tell.
**Bank need:** exactly what a model-risk reviewer wants to hear — evidence of a
real evaluation culture, not vendor claims.
**Effort:** zero — it already happened.
**Demo angle:** show the A/B table (v2 vs. the ported public model, 5 channels)
and say "we don't ship regressions dressed up as upgrades."

### #7 — Customer voice-identity + liveness fusion
**What:** beyond "is it synthetic," verify "is it *this customer's* voice" via a
voiceprint enrolled at consent, fused with active liveness challenges.
**Why it beats competitors:** combines anti-spoofing + identity — closes the gap
that voice biometrics alone leave.
**Bank need:** strong for phone-banking authentication.
**Effort:** medium-high (enrollment + speaker-verification model + consent flow). Not yet built.

### #8 — Forensic evidence pack & regulatory reporting
**What:** per flagged call, a downloadable report (layers that fired, transcript,
tactics, decision) for disputes / FIRs / suspicious-activity reports.
**Why it beats competitors:** banks need *defensible evidence*, not just a score
— for chargebacks, law enforcement, and regulators.
**Effort:** **already built** (`/cases`).

---

## 4. What actually wins a bank deal (procurement reality)

Judges/bankers score on these — make sure each has an answer:

| Buying criterion | Your answer |
|------------------|-------------|
| Accuracy **and low false positives** | Clean-audio calibration separates cleanly on our labeled set; telephony is our honestly-tracked, actively-closing gap; input-quality abstention prevents false alarms on bad lines outright |
| Works on **our** infrastructure | On-prem Docker, telephony robustness in progress with a scoped fix (#1), no audio leaves the bank |
| Compliance | RBI data-localisation, DPDP Act posture, audit trail, no-audio-retention, governance (#4, built) |
| Catches **real** fraud | Scam-script LLM catches human scammers; campaign detection (#3, built) |
| Integrates without rip-and-replace | SIPREC media-fork + REST/WS API (PRODUCT-EXPLAINER.md) |
| De-risked rollout | Shadow mode (#5, built), then enforcement |
| Explainable / auditable | Two-detector breakdown + evidence signals, /cases, evidence pack (#8, built) |
| Engineering rigor | We reject our own model upgrades when our tests say to (#6) |
| Total cost / footprint | Single stateless container, CPU-viable, scales horizontally, boots offline |

---

## 5. Recommendation

- **For the next review / finals (build):** **#1 telephony robustness** (run the
  queued GPU retrain — it's the last real gap) and lean hard on **#6** (the
  rigor story) and **#2 Hinglish**, both essentially free.
- **Already in hand, make sure they land in the pitch:** #3 campaigns, #4
  governance, #5 shadow mode, #8 evidence packs — these are *built*, not
  roadmap, and most competitors won't have any of them.
- **Heavier / later:** **#7 customer identity** (real, but needs enrollment +
  consent design).

## 6. Pitch lines to steal

- *"Every other detector works on a clean mic and dies on a phone line. We
  measured exactly how much — and we're closing it with a queued retrain, not
  a marketing promise."*
- *"They detect deepfakes. We detect fraud — including the human scammer with no deepfake at all."*
- *"We don't just score a call. We see the campaign: the same synthetic voice hitting fourteen of your customers."*
- *"Run us in shadow for 30 days. Look at the numbers on your own traffic. Then decide."*
- *"Your model-risk team can govern us from day one — drift, false-positive rate, versioning, all on a dashboard."*
- *"We tested the best public open-weights model against ours and it lost — so we didn't ship it. That's the difference between a demo and a product."*
- *"On a bad line, we don't guess. We say so, and we tell the caller how to fix it."*
