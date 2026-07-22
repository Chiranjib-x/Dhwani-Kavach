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

### 2. Business-Correspondent voiceprint + impersonation detection
Enroll every Bank Mitra's voiceprint (ECAPA — already built in `verify_app`).
Detect when "the Mitra" on a call is a clone/impostor, and keep an audit trail of
every BC-assisted transaction. A rural-specific use case that barely exists for
urban banking. **Reuses the voiceprint tier; needs a BC-enrollment flow + a
"known-agent" check.**

### 3. Aural Voice-OTP via IVR TTS
Deliver the fresh challenge digits *by voice* in the local language; the customer
repeats them. Digit parser already multilingual — this is a delivery change
(regional TTS on the challenge), not new detection.

### 4. DBT / government-scheme scam tactics
Add scheme-impersonation (PM-Kisan, MGNREGA, pension, "account seeding") as an
explicit tactic in the APP-fraud prompt so the model names the rural scam pattern.

### 5. Bhashini / AI4Bharat language adapter
India's national language-tech mission (22 languages + dialects). Plug STT/TTS
into Bhashini to cover tribal/low-resource languages Whisper struggles with —
closes the language gap *and* gives a bank/government a "built on national DPI"
story. Backend already supports an STT swap (`KV_ASR_LANG`, `KV_WHISPER_SIZE`).

### 6. District-level campaign alerting
Point the existing voiceprint-correlation at a region: when one ring sweeps a
district, proactively warn every targeted number and blocklist the voice —
protecting people who'd never report themselves.

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

## Honest limits (say them — they build trust)

- **Tribal low-resource dialects** are a real STT gap; deepfake detection still
  works, the coercion layer degrades until Bhashini/fine-tuning closes it.
- **AePS / fingerprint fraud is out of scope** (voice product) — though we protect
  the *call* that social-engineers the victim into it.
- We reach fraud crossing a **voice channel the bank can tap** (IVR/BC call); pure
  in-person or SMS-only fraud isn't covered.
- Impact depends on **integration with the BC/IVR rails** — partners matter as
  much as the tech.
