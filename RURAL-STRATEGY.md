# Gramin Kavach — protecting villagers, tribals & rural communities

How Dhwani-Kavach reaches India's rural, low-literacy, non-English, and tribal
banking population — and the features that make it work there. The guiding
principle:

> **You can't ask a non-literate villager to *operate* a security step.** No PIN
> app, no SMS-OTP to read, no portal. So the best protection is one they never
> run — passive, voice-first, invisible. That is exactly what this product is.

---

## The rural fraud reality (what we're actually up against)

- **Channel:** rural India banks by *voice and by proxy* — IVR helplines,
  Business Correspondents (Bank Mitras with micro-ATMs), feature phones. Rarely a
  smartphone app.
- **Frauds:** DBT/pension/wage-scheme impersonation ("your pension is stuck —
  share the OTP"), fake-KYC "account will be blocked", digital-arrest/police
  scams, a cloned migrant relative asking for money, and **BC impersonation /
  BC-side fraud** — the agent *is* the bank to a village.
- **Constraints:** low/zero literacy, low digital literacy, many languages and
  tribal dialects (Santali, Gondi, Bhili, Mundari — beyond Hindi), patchy
  connectivity, weak individual recourse (victims often never report).

---

## What already works today (no build needed)

| Capability | Why it fits rural |
|---|---|
| **Deepfake detection is acoustic** | 100% language- and dialect-agnostic. A cloned tribal-dialect voice flags identically to English. The headline protection needs *zero* language support. |
| **APP-fraud / coercion LLM** | Whisper auto-detects Hindi/regional → LLM reads the *coercion* — exactly the "share your OTP under pressure" vector that dominates rural loss. |
| **Voice-OTP is multilingual** | Reads Devanagari + romanized Hindi digits; spoken challenge, no screen reading required. |
| **On-prem, CPU-viable, no-internet detection** | Runs at a regional/RRB data centre or an edge box; fine on rural connectivity. |
| **Campaign / voiceprint correlation** | Detects one fraud voice sweeping a district — community-level protection where individuals don't report. |

---

## The buildable shortlist (impact order)

### 1. Real-time vernacular scam warning — **DEMO BUILT (`/rural`)**
When APP-fraud risk spikes, the IVR **speaks** a warning in the customer's
language: *"सावधान! यह कॉल धोखा हो सकती है। अपना OTP किसी को न बताएं।"* A
literacy-free intervention at the exact second of risk — the highest-impact,
most-demoable rural feature.
- **Demo:** `frontend/src/routes/rural.tsx` — three real rural scam scripts
  (pension/DBT, fake-KYC, digital-arrest), risk + tactics climb as they map to the
  live APP-fraud taxonomy, then the browser **speaks** the Hindi warning (Web
  Speech API — offline). Clearly labeled illustrative; the detection engine behind
  it is the same one demoed live on the dashboard.
- **Productionization:** drive the warning off the real `scam.score`/`escalation`
  from `/api/analyze`; deliver via the IVR's regional-language TTS (or Bhashini,
  below) instead of the browser.

### 2. Business-Correspondent voiceprint + impersonation detection — **DEMO BUILT (`/mitra`)**
Enroll every Bank Mitra's voiceprint (ECAPA — already built in `verify_app`).
Detect when "the Mitra" on a call is a clone/impostor. The BC *is* the bank to a
village, so an impersonated/cloned agent is a direct fraud node the customer can't
check. **Demo (`routes/mitra.tsx`):** three cases — genuine Mitra (VERIFIED),
stranger (voice mismatch → REJECTED), and AI clone (partly passes the 1:1
voiceprint but the synthetic-voice check catches it → REJECTED) — which shows
*why* both checks are needed. Reuses the real ECAPA engine (`/voiceprint`).

### 3. Aural Voice-OTP via IVR TTS — **BUILT (in `/verify`)**
The challenge digits are now **spoken aloud in Hindi** before recording (proper
turn-taking so the prompt isn't captured), with a "hear again" replay — so a
non-literate caller can use the OTP without reading. `routes/verify.tsx`; digit
words mapped to Devanagari, Web Speech API (offline).

### 4. DBT / government-scheme scam tactics — **BUILT (backend prompt)**
`ml/scam_detector.py` `scam_narrative`/`high_risk_intent` now explicitly name the
rural patterns: a stuck pension/DBT/PM-Kisan/MGNREGA payment needing
're-KYC'/Aadhaar-seeding/OTP, "account will be blocked" KYC threats, utility-
disconnection threats, and OTP/PIN sharing or AePS biometric withdrawals.

### 5. Bhashini / AI4Bharat language adapter — **DEMO BUILT (`/languages`)**
India's national language-tech mission (22 languages + dialects) covers the
tribal/low-resource languages Whisper struggles with. **Demo
(`routes/languages.tsx`):** the two honest layers (deepfake = language-agnostic;
coercion = Whisper-native + Bhashini), a spoken Hindi warning, and a coverage grid
by endonym (native vs Bhashini). Backend is already STT-swappable (`KV_ASR_LANG`,
`KV_WHISPER_SIZE`); the adapter drops in without touching the detectors.

### 6. District-level campaign alerting — **DEMO BUILT (`/campaign`)**
Point the existing voiceprint-correlation at a region: when one voice sweeps a
district, blocklist it and **proactively warn** the customers it hasn't reached
yet. **Demo (`routes/campaign.tsx`):** a fraud voice sweeping Rampur block across
villages, with "protect the district" firing a blocklist + a warning wave to the
still-at-risk — community protection where the individual never reports.

---

## Partners / rails to actually reach them

Regional Rural Banks · cooperative banks · **India Post Payments Bank** · NPCI
(AePS/UPI) · **CSCs** (village service centres) · **SHGs** (women's self-help
groups) · **Bhashini/AI4Bharat** (languages). These serve rural India directly —
the right pilot partners, not big private banks.

## The framing that makes a bank deploy it for low-value accounts

Jan Dhan / DBT accounts are low-balance but **massive in volume**, and the poorest
can least afford a loss — with national-priority weight behind financial
inclusion. A cheap, CPU-based, on-prem, voice-only layer that scales across
millions of accounts **with no new customer hardware** is the only economics that
work here. **Position it as protecting the financial-inclusion mission.**

## Placement — what the shield can and can't see (answer this before it's asked)

The shield sits on the **bank's own channel** (IVR / helpline / agent / Bank
Mitra). It does **NOT** see the scammer's direct call to the villager's personal
phone — that call never touches the bank's network.

So what does it catch? **The moment the fraud reaches the bank's money.** The
scammer coaches the villager offline; then the villager **contacts the bank** —
to share the OTP, "update KYC", or move money to a "safe account" — and *that*
bank-side call is where the shield hears the scam in the customer's own words and
intervenes. This is the highest-loss vector precisely because the bank is the one
about to move the money.

To intercept the scammer's **direct** call to the customer, you'd deploy at the
**telecom-operator layer** (protect every subscriber's calls) or on the
**customer's device** — a real, larger future direction, but a different customer
than a single bank's IVR. Name this honestly; it reads as rigour, and it's the
first question a bank panel will ask.

## Honest limits (say them — they build trust)

- **Placement:** catches the fraud when it reaches the bank's channel, not the
  scammer's direct call to the customer (see above; telco/device deployment is the
  path to the latter).
- **Tribal low-resource dialects** are a real STT gap; deepfake detection still
  works, the coercion layer degrades until Bhashini/fine-tuning closes it.
- **AePS / fingerprint fraud is out of scope** (voice product) — though we protect
  the *bank call* that social-engineers the victim into it.
- Impact depends on **integration with the BC/IVR rails** — partners matter as
  much as the tech.
