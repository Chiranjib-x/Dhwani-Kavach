# Dhwani-Kavach — Demo Script & Pitch Runbook (Phase A)

For the review. Goal: separate from every other "deepfake detector" team in
the first 60 seconds, then *prove* it live.

---

## The 30-second pitch (say this first)

> "Most deepfake detectors are accurate on a dataset and useless on a real call —
> they'd flag your own customers as fake. And worse, **most bank vishing isn't even
> a deepfake — it's a real human scammer**, which a deepfake-only product scores as
> safe. We didn't build a detector. We built a **real-time call-fraud shield**: it
> runs on the bank's own network, scores the live call, and gives one decision —
> Monitor, Challenge, or Block. Let me prove it right now."

Three words to repeat: **live, on-prem, decision** (not "score").

---

## The live demo — run in this exact order

> Backend `http://localhost:8000`, frontend `http://localhost:8080`.
> Hard-refresh (Ctrl+Shift+R). Scroll to "monitor a live call". Wait for the green
> **LIVE SOCKET CONNECTED** dot.

**Beat 1 — real voice is clean.**
Speak normally for ~5s (mic). → gauge **GREEN**, action **MONITOR**.
Say: *"That's me, live. Green. No false alarm — the thing dataset-trained models fail."*

**Beat 2 — the deepfake is caught.**
Play an ElevenLabs clone of your voice. → gauge **RED**, action **CHALLENGE/BLOCK**.
Say: *"Cloned voice. Red, in ~4 seconds, mid-call — before money moves."*

**Beat 3 — the differentiator: a scam with NO deepfake.**
In your *own real voice*, read a scam script:
> "This is the bank security team. Your account is compromised. Don't tell anyone.
> Transfer fifty thousand to this new account now or it's frozen."
→ tactic chips light up (**Urgency, Authority impersonation, Isolation, New beneficiary, Threat**),
scam score jumps, action escalates. Voice is real, verdict is still **CHALLENGE/BLOCK**.
Say: *"My real voice. No deepfake. Every other team's product says safe. Ours catches it — because it reads the **scam**, not just the **synthesis**."*

**Beat 4 — futureproof + compliance (one line each).**
- Point at **NOVELTY %**: *"Flags synthesis signatures it's never seen — catches the clone tool that ships next month."*
- Mention the **audit log**: *"Every verdict is logged, no audio stored — RBI-clean, audit-ready."*

---

## If they probe (have these ready)

- **"How does it integrate?"** → INTEGRATION.md: SIPREC media-fork → our WS API → agent screen / fraud engine. On-prem Docker, no audio leaves the bank.
- **"Is this production-ready?"** → Honest: live demo is real; production upgrades are marked in code (`ponytail:` comments) — mTLS, embedding-based novelty, core-banking transaction feed, SIPREC adapter. *"We built the hard part — the detection and the decision. The plumbing is standard."*
- **"Accuracy?"** → Don't lead here. *"~5% EER on modern fakes, but accuracy isn't the moat — not flagging real customers, and catching human-scammer calls, is."*

---

## Pre-demo checklist (do before you present)

- [ ] **A1** Back up `deepfake_w2v.pt` (USB + cloud + Kaggle Save Version) — single point of failure.
- [ ] `start-demo.bat` launches; both ports green.
- [ ] Mic permission granted in the browser; test Beat 1 once.
- [ ] Clone audio file ready on the desktop for Beat 2.
- [ ] Scam script for Beat 3 on a card / second screen.
- [ ] Internet up (scam layer calls NVIDIA NIM). If offline: scam layer goes neutral but voice detection still works — know this so you're not surprised.
- [ ] **A4** Full dry-run end-to-end at least twice.
