# Dhwani-Kavach — Demo Script & Pitch Runbook

For the review. Goal: in the first minute, separate from every other "deepfake
detector" team, then *prove* a real bank product live.

URLs: frontend `http://localhost:8080` (Vite bumps to `8081` if 8080 is taken —
check the terminal), backend `http://localhost:8000`.

---

## The 30-second pitch (say this first)

> "Most deepfake detectors are accurate on a dataset and useless on a real call —
> they'd flag your own customers as fake, and they miss the vishing that uses a
> *real human* scammer with no deepfake at all. We didn't build a detector. We
> built a **real-time call-fraud shield**: it runs on the bank's own network,
> scores the live call, and gives one decision — Monitor, Challenge, or Block.
> It works in Hindi, it sees fraud *campaigns*, not just single calls, and when
> the line is too bad to be sure, it **says so** instead of guessing. Let me
> prove all of it right now."

Three words to repeat: **live, on-prem, decision** (not "score").

---

## Part 1 — The live demo

### Beat 1 — file-upload analysis (dashboard, `POST /api/analyze`)

Use the labeled `sample_audio/` clips shipped in the repo.

**Real voice → GREEN.** Upload `sample_audio/Script_1.mp3.mpeg` (or any
`Script_1..5`, unmodified — **not** `lily_original.mp3` / `chris_original.mp3`,
which are documented out-of-domain outliers the deployed model still misreads —
see HANDOFF.md). → risk score single digits, **GREEN**.
*"That's a real, unmodified voice — green, no false alarm."*

**Clone → RED.** Upload `sample_audio/Script_1_clone.mp3.mpeg`. → risk score
high 90s, **RED**, action escalates to CHALLENGE/BLOCK.
*"Same script, AI-cloned. Caught — cleanly separated, not a borderline call."*

### Beat 2 — live WebRTC call (`/call`, two roles)

Open `/call` in two browser tabs (or two devices via `cloudflared`/`ngrok`).
Tab 1 → "I'm the Customer", Tab 2 → "I'm the Bank Agent". Media is peer-to-peer;
the agent side taps the incoming audio track **digitally** and streams it to the
same detection engine live.

*"This is the same integration a real telephony system uses — the audio reaches
our detector digitally, not through a laptop mic listening to a speaker. That
distinction matters: playing a deepfake through a physical speaker into a
microphone is a much harder detection problem than tapping the call itself, and
demos that fake that shortcut are demoing something a bank will never deploy."*

Speak normally into the customer tab → agent gauge reads GREEN. Play an AI clip
into that mic (or, better, share a browser tab with the clip's audio) → RED
within a few seconds.

### Beat 3 — a scam with NO deepfake (the differentiator)

In your *own real voice*, read the scam script:
> "This is the bank security team. Your account is compromised. Don't tell anyone.
> Transfer fifty thousand to this new account now or it's frozen."

→ tactic chips light up (**Urgency, Authority impersonation, Isolation, New
beneficiary, Threat**), scam score jumps, action escalates. Voice is real,
verdict still **CHALLENGE/BLOCK**.
*"My real voice, no deepfake. Every deepfake-only tool says safe. Ours catches
it — it reads the **scam**, not just the **synthesis**."*

### Beat 4 — the honest abstention (a real differentiator, not a caveat)

Cup your hand over the mic, or move to a noisy spot, and speak. → the banner
reads **INPUT QUALITY LOW** with an actionable reason, verdict is **UNCERTAIN**,
action is CHALLENGE (never a silent clear, never a false alarm on a bad line).
*"A system that confidently flags a genuine customer on a bad connection is
worse than useless. We designed ours to know what it doesn't know."*

### Beat 5 — Hindi / Hinglish

Read the scam script in Hindi/Hinglish. → tactics still fire, language shows on
the strip.
*"Your customers don't call in clean English. We handle Hindi and code-mixed
out of the box."*

### Beat 6 — shadow → enforce, one click

Click the toggle to **◐ Shadow (advisory)** → the **SHADOW · ADVISORY** badge
appears.
*"You don't flip a fraud system on at full power. Run us in shadow on your own
traffic for 30 days — we score and log, take no action. When you trust the
numbers, one switch goes live."* (Click back to Enforce.)

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

- **"How does it integrate?"** → PRODUCT-EXPLAINER.md: SIPREC media-fork → our
  WS API → agent screen / fraud engine. On-prem Docker, no audio leaves the bank.
- **"Is this production-ready?"** → Honest: the live demo is real. Production
  upgrades are marked in code (`ponytail:` comments) — mTLS, embedding-based
  novelty, the SIPREC adapter. *"We built the hard part — detection and the
  decision. The plumbing is standard."*
- **"Accuracy?"** → *"Clean-audio calibration separates real from clone cleanly
  on our labeled set today. Telephony/channel robustness is our honestly-tracked
  gap — we measure it, we don't hide it, and a targeted retrain is queued to
  close it. Accuracy isn't the moat anyway — not flagging real customers, and
  catching human-scammer calls, is."*
- **"What about a clone tool that doesn't exist yet?"** → the **NOVELTY** signal
  flags unknown synthesis signatures; confirmed frauds feed the campaign blocklist.
- **"Why did you build a second model and not ship it?"** → *"We researched the
  best public open-weights detector and ported it in specifically to test
  against ours. It lost on 4 of 5 real-world channels in our own A/B harness, so
  we didn't ship it — we don't ship what our own tests say is a regression. It's
  now the seed for our next retrain instead."* (Great answer — shows rigor.)
- **"Cost / footprint?"** → single stateless container, CPU-viable, scales
  horizontally, boots with zero external network dependency.

---

## Pre-demo checklist

- [ ] **Model backed up** (`backend/models/w2v2aasist_full.safetensors`, 306 MB,
      gitignored — USB + cloud) — single point of failure. `calibration.json`
      travels with it (paired fit).
- [ ] Backend + frontend both start clean; **`Script_1` → GREEN** sanity pass
      (any model/calibration change — verify!).
- [ ] Mic permission granted; Beat 1/2 tested once.
- [ ] **Clone audio** (`sample_audio/Script_1_clone.mp3.mpeg` or similar) ready
      to play for Beat 2.
- [ ] **Scam script** (English + Hindi) on a card / second screen.
- [ ] **Internet up** (the scam layer calls NVIDIA NIM). If offline: scam layer
      goes neutral but voice detection still works — know this so you're not
      surprised.
- [ ] Backend URLs bookmarked: `/cases`, `/campaigns`, `/governance`, `/metrics`.
- [ ] Full dry-run end-to-end at least twice, including the WebRTC `/call` beat.

## Rollback

If a model/calibration change misbehaves: stop the backend → restore the
previous `backend/models/w2v2aasist_full.safetensors` + `calibration.json` pair
from backup → restart. Never mix a bundle with a `calibration.json` fit to a
*different* bundle — it mis-scales.
