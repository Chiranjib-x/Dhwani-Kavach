# Attack Range — mock-bank demo runbook

The stage plan for the `/range` demo: a mock bank running the shield, an attacker
launching THREAT.md vectors at it, and a master **Shield ON/OFF** toggle. The
whole pitch is one A/B — *watch the money leave, then flip the switch and watch
it get stopped.*

> This is the **how-to-run-it-live** doc. The attack taxonomy is in
> [THREAT.md](THREAT.md); the phase-wise with/without narrative is in
> [ATTACK-DEMO-PLAN.md](ATTACK-DEMO-PLAN.md); stage discipline (clips, channels)
> is in [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md).

---

## What the mock bank is (and isn't)

- **Is:** a single screen — a requested transfer (amount + beneficiary), the live
  shield verdict, and one outcome banner (**COMPLETED** / **STOPPED**). A prop
  that makes the money visible.
- **Isn't:** a banking app. No login, no ledger, no accounts. Every minute spent
  building bank UI is a minute not spent on the shield. If a judge wants "real
  banking," that's the SIPREC integration slide, not this demo.

**Why the toggle wins:** it converts an abstract claim ("we detect fraud") into a
visceral before/after on the same attack. The panel sees the value without you
narrating it.

---

## Setup (T-5 min)

1. `start-fresh.bat` — brings up backend `:8000`, verify service `:8001`,
   frontend `:8080`. Wait for all three windows.
2. Confirm the attack clips exist: `frontend/public/attacks/{clone,replay,normal}.mp3`.
   If missing (fresh machine): `python tools/prep_attack_clips.py`.
3. Open `localhost:8080/range`. Leave **Shield ON**.
4. One dry run of the clone attack — confirm it reads **BLOCK / risk 97**. If the
   backend is cold the first call is slow; get that out of the way now.

**Pre-flight checklist**
- [ ] `:8000/health` OK, `:8001/v2/health` shows `models_loaded: true`
- [ ] `/range` loads, all three attacks selectable
- [ ] Clone attack, Shield ON → BLOCK (dry run done)
- [ ] Projector/screen shows the outcome banner clearly from the back of the room

---

## The run (≈4 min)

The order is deliberate: establish the danger, prove the catch, then show it
doesn't cry wolf.

### Act 1 — the undefended bank (60s)
1. **Shield OFF** (toggle red).
2. Select **AI voice clone**, **Launch**.
3. Verdict panel greys out — *"not consulted, shield off."* Outcome:
   **✗ TRANSFER COMPLETED — ₹5,00,000 left the account.**

> *"This is a bank today with no audio-forensics layer. A cloned customer voice
> authorised a five-lakh transfer to a brand-new payee. The bank finds out when
> the real customer disputes it — days later, money gone."*

### Act 2 — flip the switch (60s)
4. **Shield ON** (toggle green).
5. Same **AI voice clone**, **Launch**.
6. Verdict: **BLOCK · risk 97 · RED**, escalation chip **↳ step-up voice-OTP**.
   Outcome: **✓ TRANSFER STOPPED.**

> *"Same attack. Nothing changed but the shield. Two independent neural detectors
> flagged the clone in about three seconds — on the agent's screen, mid-call —
> and the money never moved. And it doesn't dead-end: it hands the caller to a
> live spoken-digit voice-OTP a recording can't answer."*

### Act 3 — the channel bypass (45s)
7. Keep **Shield ON**. Select **Loudspeaker replay**, **Launch**.
8. Verdict: **BLOCK/CHALLENGE**, **replay signature** chip.

> *"Attackers know detectors hunt artifacts — so they play the clone through a
> speaker, and the air hop smears those artifacts. We catch the channel instead:
> the low- and high-frequency deficits a real near-field voice never has. The one
> thing it will never do is silently trust a speaker playback."*

### Act 4 — no false alarms (30s)
9. Keep **Shield ON**. Select **Genuine customer**, **Launch**.
10. Verdict: **MONITOR · GREEN**. Outcome: **✓ TRANSFER COMPLETED** (known payee).

> *"And a real customer on a routine payment sails through — GREEN, no friction.
> A shield that blocks everything is useless; this one only acts on a real signal."*

**Close:** *"One toggle, one attack, two worlds. That's the difference this layer
makes — and it drops into your contact centre behind a SIPREC fork, on-prem, no
audio leaving the bank."*

---

## The APP-fraud variant (optional, +45s)

The strongest story if the panel is fraud-ops rather than pure tech: a **real**
customer being coached. It's not in the three canned buttons because the
LLM verdict depends on a live NIM call (latency/failure risk mid-demo). If you
want it live, pre-warm it and use the `/` upload with a coached-transfer script
(see [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md) §3). Point:

> *"Here the voice is 100% real — biometrics pass, deepfake detection passes.
> Every pure-detector on the market is blind. We read the conversation, flag the
> coercion, and route to a human — because no voice test can clear a coerced real
> customer. That honesty is the product."*

---

## If a judge pushes

| They say | You do / say |
|---|---|
| *"Play a clone into the mic right now."* | Expect the **replay gate** → CHALLENGE. Narrate it as a feature: *"open-air smears artifacts; the channel gate catches it anyway."* Never rely on artifact detection through room air. |
| *"Isn't OFF just faked to block?"* | Show it honestly: OFF means the verdict is **never consulted** — the transfer completes regardless of what the shield would have said. The A/B is real. |
| *"What about an attack you haven't seen?"* | Live voice-conversion & adversarial evasion are the honest frontier (THREAT #4/#9). The retrain + red-team loop is the answer; the quality gate abstains rather than false-clear. |
| *"Is this real-time?"* | ~3s on upload, ~4–6s streaming — inside the 10-second budget the problem statement names. |

---

## Failure modes & fallbacks

- **Backend down / clip 404** → the attacker console shows the error; re-run
  `start-fresh.bat`, re-check `frontend/public/attacks/`.
- **Verdict wobbles on a clip** → the three clips are pre-verified
  (clone 97 / replay 96 / normal 1). If a retrain changed the model, re-verify
  with `cd backend && python -m eval.run ../Dataset_orig` before trusting them.
- **Verify service cold** → the escalation *chip* still shows (it's from the
  shield verdict); only clicking through to `/verify` needs `:8001` warm.
- **Total backend failure** → fall back to the phase-wise narration in
  [ATTACK-DEMO-PLAN.md](ATTACK-DEMO-PLAN.md); the story survives without the tool.

---

## One-line cheat sheet (tape to the laptop)

```
OFF + clone   -> COMPLETED (money gone)   "undefended bank"
ON  + clone   -> BLOCK 97  (stopped)      "same attack, shield on"
ON  + replay  -> BLOCK     (replay chip)  "catch the channel"
ON  + genuine -> MONITOR   (completed)    "no false alarms"
```
