# Attack Demo Plan — the threat model, staged live, with vs without the shield

A phase-wise script for demonstrating the [THREAT.md](THREAT.md) vectors on stage.
For each attack: **the scenario**, **how to stage it safely on our own dashboard**,
**what the bank sees WITHOUT the product**, **what happens WITH it**, and the
**one-line panel takeaway**.

> **Scope & ethics.** Every "attack" here is simulated against *our own* demo
> instance with *our own* recordings and tools (`tools/demo_synth.py`, ElevenLabs
> clips already in `Dataset_orig`, replay-simulated files). Nothing targets a real
> bank, a real person's account, or a live phone line. This is a detection demo,
> not an attack playbook — it stays at THREAT.md's taxonomy level.
>
> Staging channels and verified clips: [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md).
> The "with product" walkthrough of each layer: [DEMO-SHOWCASE.md](DEMO-SHOWCASE.md).

---

## The framing slide (open every attack demo with this)

Three trust assumptions banks rely on, and which cheap attacks now break them:

- **A1 — "the voiceprint proves identity."** Broken by seconds-of-audio cloning.
- **A2 — "an agent can tell a real caller from a fake."** Broken by the same clone.
- **A3 — "OTP / security questions confirm intent."** Always socially engineerable.

*"A review that only hardens OTP is fighting the last war. We show three attacks
that walk past today's controls — and where each of our layers stops them."*

---

## Phase 0 — Baseline: the undefended bank (60 s, no software)

Show nothing running. Narrate the status quo: caller-ID matches, the voice "sounds
right," the agent is trained to trust both. **This is the entire current control
set.** Every attack below starts from here.

**Without product, universally:** the fraud is *invisible at decision time*. The
bank finds out when the customer disputes the transfer — days later, money gone.

---

## Phase 1 — Tier 1: cheap, scalable, defeats a primary control

Lead here. These are the highest-danger vectors (THREAT.md §Tier 1).

### 1A · Synthetic-voice biometric defeat (THREAT #1, defeats A1)
- **Scenario:** seconds of harvested audio → a clone that matches the enrolled
  voiceprint.
- **Stage it:** upload a verified clone (`aditya_17-clone`, reads 97) to `/`.
- **WITHOUT:** voice biometric says "match" → caller is "verified." Full access.
- **WITH:** **RED / HIGH RISK** in ~3 s, ARTIFACT WINDOW outlined, dual neural
  detectors both fire. Action escalates to CHALLENGE/BLOCK.
- **Takeaway:** *"The most-trusted control — the voiceprint — is the most cleanly
  broken. We score the audio the biometric trusted blindly."*

### 1B · Agent-assisted transfer via clone (THREAT #2, defeats A2)
- **Scenario:** attacker calls the contact centre *as the customer*, clone speaking,
  to authorise a transfer / add a payee.
- **Stage it:** the `/call` WebRTC demo in two tabs (Customer / Bank Agent); the
  agent side streams the received clone audio to the detector (runbook §1).
- **WITHOUT:** the agent hears a normal customer and processes the transfer.
- **WITH:** a **RED banner on the agent's screen, mid-call**, before authorisation.
  The fused action reads BLOCK on a new payee.
- **Takeaway:** *"The fraud and the defense happen in the same ten seconds — on the
  agent's screen, not in a next-day dispute."*

### 1C · Human scam-script, NO deepfake (THREAT #3, defeats A2+A3) — the headliner
- **Scenario:** a real human coerces a genuine customer (or impersonates the bank).
  The voice is 100% real. **Invisible to every pure-deepfake detector on the
  market.**
- **Stage it:** upload a clip of the coached-transfer script (SHOWCASE §4 / runbook
  §3) — watch APP-FRAUD RISK and the tactic chips.
- **WITHOUT:** deepfake detection passes (real voice), biometrics pass (it's them) —
  *both green lights, and the customer authorises their own loss.*
- **WITH:** APP-FRAUD RISK climbs, chips fire (**Under duress · Scam narrative ·
  Pays a stranger**), action → CHALLENGE, and escalation **routes to a human +
  cooling-off** — the only correct response, because no voice test can clear a
  coerced real customer.
- **Takeaway:** *"This is the single most dangerous vector — free, high-volume, the
  biggest share of real vishing loss — and it's the one a deepfake-only tool can't
  even see. We lead with it, not the flashy clone."*

---

## Phase 2 — Tier 2: serious, higher cost or narrower window

### 2A · Loudspeaker / over-the-air replay (THREAT #5)
- **Scenario:** a pre-made clone played into a live call — the air hop smears the
  synthesis artifacts, beating most artifact detectors.
- **Stage it:** replay-simulated clip, or (if a judge insists) play a clone at the
  laptop mic.
- **WITHOUT:** artifact detectors read *cleaner* after the air hop — a false
  all-clear on the exact bypass attackers use in the field.
- **WITH:** **Loudspeaker replay suspected** (LF+HF band deficits), action forced to
  **CHALLENGE**; `/verify` rejects outright — "correct digits, untrusted channel."
- **Takeaway:** *"The one thing it will never do is silently trust a speaker
  playback. Catch the channel, not just the artifact."*

### 2B · Real-time voice conversion (THREAT #4) — **the honest hard case**
- **Scenario:** attacker speaks; a streaming model re-timbres to the target voice
  live, so it can answer challenges.
- **Stage it:** describe it; optionally show a conversion sample scoring lower than
  a clean clone.
- **WITHOUT:** defeats naive liveness and voice biometrics together.
- **WITH:** the detector sees conversion artifacts *and* Voice-OTP timing/latency
  analysis adds a second axis — **but be honest:** this is the frontier, the case
  the channel-robust retrain targets.
- **Takeaway:** *"We tell you what we don't fully solve yet. The retrain loop and
  red-team pipeline are the answer to 'what about attacks you haven't seen' — that
  honesty is worth more than a claim of total coverage."*

### 2C · SIM-swap / caller-ID spoof + clone (THREAT #6)
- **Scenario:** take over or spoof the number so metadata "confirms" the customer,
  then clone the voice — two factors fall at once.
- **Stage it:** narrate; upload the clone with a note that "the number checked out."
- **WITHOUT:** metadata + biometric both say yes; the call sails through.
- **WITH:** **we ignore metadata and judge the audio** — a spoofed number with a
  clone still gets scored RED.
- **Takeaway:** *"We don't trust the number. A perfect caller-ID with a clone behind
  it is still a clone to us."*

---

## Phase 3 — Tier 3: situational or higher-skill

Cover briefly; these show breadth and intellectual honesty.

| Attack | Without product | With product |
|---|---|---|
| **Enrolment poisoning** (#7) — enrol a synthetic/attacker voice at onboarding | later "matches" are legitimately theirs, permanent | transaction-time anomaly detection still flags; **honest:** the real fix is hardening enrolment (defence-in-depth beyond us) |
| **Recorded-snippet splicing** (#8) — stitch captured "yes"/account-no fragments for a scripted IVR | satisfies a static IVR prompt | phase-coherence + neural flag the splice seams; **dynamic-digit Voice-OTP defeats it by construction** — fresh code every attempt |
| **Adversarial-perturbation evasion** (#9) — perturbations tuned to push *our* detector toward "real" | n/a (an attack on us) | **our documented untested limitation** — the quality-gate abstains rather than emit a false-clean; naming it first in Q&A reads as rigour |
| **Insider / vishing-the-agent** (#10) — social-engineer the helpdesk or bribe an insider | bypasses the check entirely | no audio product solves the human layer; we contribute the **audit trail** that makes abuse detectable after the fact |

---

## Phase 4 — The synthesis slide (close the attack demo)

Land the three-part structure from THREAT.md:

1. **Exposure is worst where controls feel strongest** — voice biometrics (A1) and
   caller-ID (metadata) are the most-trusted and most cleanly defeated (#1, #6).
2. **The vectors cluster into three defenses, and we have a layer for each:**
   *is the voice synthetic* (dual detectors) · *is the script a scam* (APP-fraud
   LLM) · *is the channel trustworthy* (replay + quality gates) — then the flagged
   call **escalates into voice-OTP / 1:1 voiceprint / human review.**
3. **We're honest about #4 and #9** (live conversion, adversarial) — the retrain +
   red-team loop is the answer, and saying so convinces more than claimed total
   coverage.

*"A point solution — just a deepfake classifier, or just voice biometrics — leaves
two-thirds of this surface open. The whole surface is the product."*

---

## Timing

| Cut | Phases | Length |
|---|---|---|
| **Full** | 0 → 1 → 2 → 3 → 4 | ~9 min |
| **Standard** | 0, 1 (all), 2A+2B, 4 | ~6 min |
| **Lightning** | 1C (headliner) + 1A + 2A + 4 | ~3 min |

Never cut **1C** (human scam-script — the differentiator) or **2B/§4** (the honest
frontier — where the rigour points show).
