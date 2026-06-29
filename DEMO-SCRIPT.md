# Dhwani-Kavach — Demo Script & Pitch Runbook

For the review. Goal: in the first minute, separate from every other "deepfake
detector" team, then *prove* a real bank product live.

URLs: frontend `http://localhost:8080`, backend `http://localhost:8000`.

---

## The 30-second pitch (say this first)

> "Most deepfake detectors are accurate on a dataset and useless on a real call —
> they'd flag your own customers as fake, and they miss the vishing that uses a
> *real human* scammer with no deepfake at all. We didn't build a detector. We
> built a **real-time call-fraud shield**: it runs on the bank's own network,
> scores the live call, and gives one decision — Monitor, Challenge, or Block.
> It works on your actual phone lines, in Hindi, and it sees fraud *campaigns*,
> not just single calls. Let me prove all of it right now."

Three words to repeat: **live, on-prem, decision** (not "score").

---

## Part 1 — The live demo (dashboard, http://localhost:8080)

Hard-refresh (Ctrl+Shift+R). Scroll to "monitor a live call". Wait for the green
**LIVE SOCKET CONNECTED** dot. Leave the toggle on **● Enforce (live)** to start.

**Beat 1 — real voice is clean.**
Speak normally ~5s (mic). → gauge **GREEN**, action **MONITOR**.
*"That's me, live. Green. No false alarm — the thing dataset-trained models fail."*

**Beat 2 — the deepfake is caught.**
Play an ElevenLabs clone of your voice. → **RED**, action **CHALLENGE/BLOCK** in ~4s.
*"Cloned voice. Red, mid-call, before money moves."*

**Beat 3 — a scam with NO deepfake (the differentiator).**
In your *own real voice*, read the scam script:
> "This is the bank security team. Your account is compromised. Don't tell anyone.
> Transfer fifty thousand to this new account now or it's frozen."
→ tactic chips light up (**Urgency, Authority impersonation, Isolation, New beneficiary, Threat**), scam score jumps, action escalates. Voice is real, verdict still **CHALLENGE/BLOCK**.
*"My real voice, no deepfake. Every other team's product says safe. Ours catches it — it reads the **scam**, not just the **synthesis**."*

**Beat 4 — works on a real phone line.**
Play the **phone-filtered** clone (`clone_phone.wav`, see prep below). → still **RED**.
*"Same clone through an 8 kHz phone codec. Still caught. Our model is trained on telephony — 4% clean, 6% on phone lines. Every laptop-mic demo dies here; ours doesn't."*

**Beat 5 — Hindi / Hinglish.**
Read the scam script in Hindi/Hinglish. → tactics still fire, language shows on the strip.
*"Your customers don't call in clean English. We handle Hindi and code-mixed out of the box."*

**Beat 6 — shadow → enforce, one click.**
Click the toggle to **◐ Shadow (advisory)** → the **SHADOW · ADVISORY** badge appears.
*"You don't flip a fraud system on at full power. Run us in shadow on your own traffic for 30 days — we score and log, take no action. When you trust the numbers, one switch goes live."* (Click back to Enforce.)

---

## Part 2 — It's a deployable bank product (backend URLs)

Open these in the browser — they show this is production, not a toy:

- **`http://localhost:8000/cases`** — flagged-call **audit trail**. Click any call →
  an **evidence pack** (verdict, layers, tactics, language, transcript — *no audio
  stored*). *"Defensible evidence for disputes, FIRs, regulators."*
- **`http://localhost:8000/campaigns`** — **fraud-ring view**: the same synthetic
  voice across multiple calls. *"We don't just score a call — we see the campaign."*
- **`http://localhost:8000/governance`** — **model governance**: TPR/FPR from
  analyst labels, verdict drift, champion/challenger registry. *"Your model-risk
  team can govern us from day one — RBI Model Risk Management, built in."*
- **`http://localhost:8000/metrics`** — Prometheus, scrapes into the bank's monitoring.

On a `/cases` evidence page, click **Mark FRAUD / Mark LEGIT** → refresh
`/governance` → TPR/FPR updates live. *"Analysts label, the system measures itself."*

---

## Part 3 — If they probe (have these ready)

- **"How does it integrate?"** → INTEGRATION.md: SIPREC media-fork → our WS API →
  agent screen / fraud engine. On-prem Docker, no audio leaves the bank.
- **"Is this production-ready?"** → Honest: the live demo is real. Production
  upgrades are marked in code (`ponytail:` comments) — mTLS, embedding-based
  novelty, core-banking transaction feed, the SIPREC adapter. *"We built the hard
  part — detection and the decision. The plumbing is standard."*
- **"Accuracy?"** → *"4% clean, 6% on phone lines on modern fakes — but accuracy
  isn't the moat. Not flagging real customers, and catching human-scammer calls, is."*
- **"What about a clone tool that doesn't exist yet?"** → the **NOVELTY** signal
  flags unknown synthesis signatures; confirmed frauds feed the campaign blocklist.
- **"Cost / footprint?"** → single stateless container, CPU-viable, scales horizontally.

---

## Pre-demo checklist

- [ ] **Model backed up** (`deepfake_w2v.pt`, USB + cloud + Kaggle Save Version) — single point of failure.
- [ ] `start-demo.bat` launches; both ports green; **real-voice → GREEN** sanity pass (model changed — verify!).
- [ ] Mic permission granted; Beat 1 tested once.
- [ ] **Clone audio** on the desktop for Beat 2.
- [ ] **Phone-filtered clone** for Beat 4 — generate it once (from `backend/`):
  ```bash
  python -c "import sys; sys.path.insert(0,'.'); import librosa, soundfile as sf; from ml.telephony import to_telephony; y,_=librosa.load(r'PATH\TO\clone.wav', sr=16000, mono=True); sf.write(r'clone_phone.wav', to_telephony(y), 16000)"
  ```
- [ ] **Scam script** (English + Hindi) on a card / second screen.
- [ ] **Internet up** (the scam layer calls NVIDIA NIM). If offline: scam layer goes neutral but voice detection still works — know this so you're not surprised.
- [ ] Backend URLs bookmarked: `/cases`, `/campaigns`, `/governance`, `/metrics`.
- [ ] Full dry-run end-to-end at least twice.

## Rollback
If the new model misbehaves on real voices: stop backend → rename
`deepfake_w2v_v1.pt` back to `deepfake_w2v.pt` → restart. (You'll lose telephony
robustness but regain the prior behaviour.)
