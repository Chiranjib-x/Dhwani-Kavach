# Dhwani-Kavach
### Real-time call-fraud shield for banks — stops AI voice clones *and* human scams, on-prem, in real time.

---

**The problem.** Fraudsters clone customer or staff voices, or run scripted
social-engineering scams, to authorise transfers. OTP and voice biometrics don't
stop a convincing clone or a coerced genuine customer.

**What it does.** Listens to a call and, in seconds, returns one decision —
**MONITOR / CHALLENGE / BLOCK** — with a risk score, an explainable breakdown, and
an honest **UNCERTAIN** verdict when the input quality can't be trusted (rather
than a confident guess).

---

### Architecture

Two **independent** neural detectors carry the verdict — different architectures,
different training data, different failure modes, fused 50/50:

1. **`detector_v2`** — wav2vec2-XLS-R-300M + a W2VAASIST graph-attention head
   (Codecfake-trained: a codec/compression-artifact specialist).
2. **`detector_v3`** — wav2vec2-XLSR-53 fine-tuned specifically on modern
   commercial voice-clone engines (ElevenLabs, Polly, etc.) — matches the actual
   clone threat directly.

Four acoustic heuristics (spectral/MFCC, breath pattern, phase coherence,
liveness) are computed and shown as human-readable **evidence**, but carry
**zero vote weight** — measured to be near-noise; giving them weight only diluted
a confident verdict toward AMBER. Plus:

- **Input-quality gate** — level/clipping/SNR. Too degraded to trust → **UNCERTAIN**
  with an actionable reason ("move to a quieter place"), never a silent guess.
- **Scam-script layer** — Whisper → LLM (Nemotron) → tactic tags, for the *real
  human* scammer a deepfake-only tool would miss entirely.
- **Novelty / zero-day** — model uncertainty flags an unfamiliar synthesis
  signature before it's a known attack.
- **Campaign detection** — voiceprint clustering across calls; the same synthetic
  voice hitting multiple customers gets blocklisted.
- **Governance** — TPR/FPR from analyst labels, drift, model versioning, audit
  trail (no audio stored) — RBI Model Risk Management, built in.

Full architecture, verified numbers, and honest limitations: **[TECHNICAL-OVERVIEW.md](TECHNICAL-OVERVIEW.md)**.
Living engineering context (what's built, what's next, known gaps): **[HANDOFF.md](HANDOFF.md)**.

---

### Quick start

```bash
# Backend  -> http://localhost:8000
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --port 8000

# Frontend -> http://localhost:8080 (Vite; bumps to 8081 if 8080 is taken — check the terminal)
cd frontend && npm install && npm run dev
```
Live WebRTC call demo: `/call` on the frontend (two roles — Customer / Bank
Agent). File-upload analysis: `POST /api/analyze`. A fresh clone needs the
fine-tuned model bundle — see [HANDOFF.md](HANDOFF.md) for how to get it.

### Why it's worth it
- Closes the voice-fraud gap **OTP and biometrics leave open** — and catches
  **human scams too**, not only deepfakes.
- **Real-time** — acts during the call, before money moves.
- **On-prem, no audio retained** — RBI data-localisation aligned, minimal data risk.
- **Honest about uncertainty** — abstains instead of guessing on a bad mic/line,
  and every accuracy claim in this repo is backed by a reproducible eval, not a
  marketing number.
- **Fraud-ring intelligence** that gets smarter with every call.

### How it fits in
On-prem **Docker** container in the bank's DMZ. Integrates via a standard
**SIPREC / media-fork** from existing telephony (Genesys/Avaya/Cisco) → verdict
to the agent screen or the fraud-decisioning engine. **No rip-and-replace.**
See **[PRODUCT-EXPLAINER.md](PRODUCT-EXPLAINER.md)** for the full deployment and
integration guide.

### Repo map
| File | For |
|---|---|
| [HANDOFF.md](HANDOFF.md) | Engineers continuing this work — current state, how to run, known gaps |
| [TECHNICAL-OVERVIEW.md](TECHNICAL-OVERVIEW.md) | Technical reviewers — architecture, training, honest limitations |
| [PRODUCT-EXPLAINER.md](PRODUCT-EXPLAINER.md) | Bank IT / fraud teams — what it does, how it deploys and integrates |
| [COMPETITIVE-EDGE.md](COMPETITIVE-EDGE.md) | Positioning — where commodity detectors lose a bank deal, and how we don't |
| [DEMO-SCRIPT.md](DEMO-SCRIPT.md) | Running the live demo |
| [PLATFORM-BLUEPRINT.md](PLATFORM-BLUEPRINT.md) | Target architecture for the platform beyond the hackathon |
| [PHASE-H-KAGGLE.md](PHASE-H-KAGGLE.md) | The channel-robustness retrain runbook (Kaggle GPU) |
| [security/](security/) | Threat library + the automated security-review agent |
