# Demo Showcase — every layer, in the order that tells the story

A staged walkthrough that lights up **all** of Dhwani-Kavach's layers on screen,
built so each station adds one idea on top of the last. Ends on the piece that
ties it together: a flagged call is not a dead end — it **escalates into active
verification**. Two apps, one funnel.

> Staging discipline (channels, verified clips, the golden "never speaker→air→mic"
> rule) lives in [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md). This doc is the *narrative
> order*; the runbook is the *safe inputs*. Read both before stage.
>
> All numbers are the measured set: **99.2% acc · EER 1.6% · AUC 0.999** (122-clip
> Dataset_orig, `cd backend && python -m eval.run ../Dataset_orig`). Telephony is
> the known gap (~20% EER) — say so when asked; honesty is a scoring asset.

---

## The arc (why this order)

The judges' instinct is "it's just a deepfake classifier." The walk dismantles
that in five moves:

1. **It detects** — the neural core, fast, on the spectrogram (the literal ask).
2. **It detects honestly** — abstains when it can't judge; never a false all-clear.
3. **It detects what a classifier can't** — the channel (replay) and the *content*
   (a coerced human, no deepfake at all).
4. **It decides** — fuses everything into one bank-actionable action + txn context.
5. **It closes the loop** — the decision escalates into voice-OTP / 1:1 voiceprint,
   or to a human when the customer is real-but-coerced. ← the integration.

Then the bank-grade surfaces (cases, campaigns, governance) show it's a product,
not a notebook.

---

## Station 1 — Neural core, on the spectrogram, in <10 s

**Surface:** dashboard `/` → "Stream a file" (or mic via VB-Cable).
**Input:** a verified fake (`aditya_17-clone`, reads 97) then a verified real
(`aditya_10`, reads 0).

**What lights up:**
- Live 128-band **spectrogram**; on RED the **ARTIFACT WINDOW** outlines the exact
  4 s region just scored.
- **HIGH RISK** banner: "synthetic artifacts detected — micro-imperfections in
  pitch/frequency."
- **flagged at X.Xs · 10 s budget ✓** (upload ~3 s, stream ~4–6 s).
- Layer bars: **Neural · XLS-R deepfake** and **Neural · Clone specialist** both
  drive it.

**Say:** *"Two independent neural detectors — different training data, so their
failure modes anti-correlate. This is the literal ask: read the spectrogram of a
live call, flag High Risk inside ten seconds. There's the clock."*

**Why two detectors matter (the generalization story):** a single SSL detector
scored <0.5% on our dev set but **40% EER** on real clones. Two anti-correlated
detectors + calibration is how we got to 1.6%. Lead with this if a judge is an ML
person — it's the most defensible slide.

---

## Station 2 — The honesty layer (input-quality abstention)

**Input:** a deliberately bad clip — very quiet, or clipped, or the room mic in a
noisy hall.

**What lights up:** the **INPUT QUALITY LOW** banner (cyan), verdict **held** as
**UNCERTAIN**, with the exact reason ("too quiet", "clipping", "background noise")
and the SNR.

**Say:** *"A laundered deepfake reads unreliable, not clean. So when we can't trust
the audio, we don't guess — we abstain and say why. A detector that never says 'I
don't know' is the one that greenlights the attack it couldn't hear."*

This is the pre-emptive answer to "what about adversarial / degraded audio" (THREAT
#9) — we don't pretend the score is trustworthy when it isn't.

---

## Station 3 — The channel gate (loudspeaker replay)

**Input:** a clone processed to simulate loudspeaker→air→mic (see runbook §1); or,
if a judge forces the open-air test, just play a clone at the laptop.

**What lights up:** **Loudspeaker replay suspected** chip (red), action forced to
**CHALLENGE** — a suspected replay **can never clear to MONITOR** on the voice
score alone.

**Say:** *"Playing a clone through a speaker smears the very artifacts every
detector hunts for — it's the #1 field bypass. We catch the channel instead of the
artifact: low- and high-frequency band deficits a real near-field voice always has.
Either the model catches the synthesis, or the channel gate catches the replay."*

Verified: **0** false replay flags across all 122 normal clips; speaker-simulated
clone → suspect, score 95, CHALLENGE.

---

## Station 4 — The content layer (APP-fraud / coerced customer)

The differentiator no deepfake-only tool has. **The voice is 100% real** — a
genuine customer being coached/coerced in real time.

**Surface:** upload a clip whose *words* are a coached-transfer script; watch the
**APP-FRAUD RISK n/100** meter and the tactic chips.
**Script that fires reliably:**

> "They told me my account isn't safe and I have to move everything to the new
> account they set up right now, and I mustn't hang up or tell anyone at the bank."

**What lights up:** APP-FRAUD RISK climbs; chips **Under duress · Scam narrative ·
Pays a stranger · High-risk request**; language tag (Hindi/English auto-detected).

**Say:** *"Voice biometrics pass — it's really them. Deepfake detection passes — the
voice is real. Every pure-detector on the market is blind here. We read the
*conversation*: a real customer being socially engineered. This is the largest
share of real vishing loss."*

---

## Station 5 — Fusion (score → decision a bank can act on)

**Input:** re-run a fake **with transaction context** set — enter an amount above
₹50,000 or tick **NEW BENEFICIARY**.

**What lights up:** the **RECOMMENDED ACTION** flips MONITOR → **CHALLENGE** →
**BLOCK** as the context sharpens, with a one-line auditable reason
("synthetic-voice risk 96 + new payee → BLOCK").

**Say:** *"Banks act on decisions, not scores. Same voice, different money-at-risk,
different action — and every decision is one plain sentence an auditor can read.
Rule-based on purpose: explainable beats clever when a regulator asks why."*

---

## Station 6 — The loop closes: escalation → step-up (the integration)

This is the new piece and the strongest ending: **the flagged call routes into
verification automatically.**

**What lights up:** under any CHALLENGE/BLOCK, a step-up strip appears:
- **↳ STEP-UP REQUIRED — Run Voice-OTP ↗** for a synthetic/replay/low-quality flag.
- **↳ ROUTE TO HUMAN** when the driver is *coercion* — because a coached real
  customer passes every voice check, so a second voice gate is theatre.

**Click "Run Voice-OTP ↗" → `/verify`:**
- The screen issues **fresh random digits**; you read them in a 6 s window.
- Backend checks **content** (ASR — a recording can't answer new digits) **and** the
  **deepfake ensemble** (a live TTS rig that answers still fails) **and** the
  **replay gate** ("correct digits, untrusted channel" → reject).
- Verdict: **✓ VERIFIED** / **✗ REJECTED** with expected vs heard digits.

**Then the 1:1 identity app** (`backend/verify_app/`, [MASTER-PLAN.md](MASTER-PLAN.md)):
enroll a voice once (3 prompts), then verify — the **ECAPA speaker gate** confirms
*this specific customer*, not just "a live human." Content + liveness + **identity**,
with enrollment, lockout, and an audit trail.

**Say:** *"Detection flags the call; it doesn't end there. A synthetic or replayed
voice gets a live spoken-digit challenge plus a one-to-one voiceprint match — a
recording or a speaker playback physically can't complete it. A coerced *real*
customer can't be cleared by any voice test, so we route them to a human and a
cooling-off before the money moves. Passive detection and active verification, one
funnel."*

---

## Station 7 — It's a product (bank-grade surfaces)

Fast tour, backend pages (`:8000`):

| Surface | The point |
|---|---|
| **/cases** | per-call **evidence pack** — score, layers, transcript, waveform. What the fraud analyst actually opens. |
| **/campaigns** | voiceprint correlation — "same voice across 5 calls" / known-fraud blocklist hit. One clone rarely calls once. |
| **/governance** | TPR/FPR, drift, model registry, labelling. The MRM/audit view a bank compliance team demands. |
| **/metrics** | Prometheus endpoint — it plugs into their existing monitoring. |

**Say:** *"On-prem, SIPREC tap, no audio leaves the bank. This isn't a demo notebook
— it's the analyst console, the campaign view, and the governance page a bank needs
to actually deploy it."*

---

## One-breath close

*"One call, five defenses in parallel — is the voice synthetic, is the channel
real, is the customer being coerced — fused into one explainable action, that then
**escalates into voice-OTP, a voiceprint match, or a human**. A point solution
covers one of those. We cover the surface."*

---

## Compressed run sheet (tape to the laptop)

| # | Surface | Input | Audience sees | Time |
|---|---|---|---|---|
| 1 | `/` stream | `aditya_17-clone` → `aditya_10` | RED+artifact window+10 s clock → GREEN | 60 s |
| 2 | `/` stream | quiet/clipped clip | UNCERTAIN, "held", reason | 25 s |
| 3 | `/` stream | replay-sim clip | "Loudspeaker replay suspected" → CHALLENGE | 30 s |
| 4 | `/` upload | coached-transfer script | APP-FRAUD chips, language tag | 40 s |
| 5 | `/` upload | fake + ₹>50k / new payee | action → BLOCK, one-line reason | 30 s |
| 6 | strip → `/verify` | read the digits live | STEP-UP → ✓ VERIFIED / ✗ REJECTED | 60 s |
| 7 | `:8000/cases…` | — | evidence / campaign / governance | 45 s |

Total ≈ 5 min. Drop stations 2–3 for a 3-min cut; never drop 1, 4, 6.
