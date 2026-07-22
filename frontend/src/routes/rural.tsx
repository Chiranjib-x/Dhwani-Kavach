import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Gramin Kavach — the rural intervention. IMPORTANT placement note: the shield
// sits on the BANK's own channel (IVR / helpline / Business-Correspondent call),
// NOT on the scammer's direct call to the villager (that never touches the bank).
// The scammer targets the villager offline; when the targeted villager then
// CONTACTS THE BANK -- confused, or to do what they were told (share an OTP, move
// money to a "safe account") -- the shield hears the scam in their own words and
// SPEAKS a warning back, literacy-free, at the moment of risk. This is the same
// APP-fraud vector the product is built for: a real customer on the bank line
// being manipulated.
//
// Illustrative scenario (clearly labeled): the dialogue is scripted to real rural
// scams and the tactics map to the same taxonomy the APP-fraud LLM detects live.
// The intervention is real — the warning is spoken by the browser (Web Speech
// API, offline).

export const Route = createFileRoute("/rural")({ component: RuralShield })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Who = "bank" | "villager"
type Line = { who: Who; hi: string; en: string; tactics?: string[]; addRisk?: number }
type Scenario = { id: string; label: string; sub: string; lines: Line[]; warnHi: string; warnEn: string }

const TACTIC_LABEL: Record<string, string> = {
  scam_narrative: "Scam narrative", duress: "Under duress", high_risk_intent: "High-risk request",
  coaching: "Being coached", third_party_benefit: "Pays a stranger",
}

// The villager has CALLED THE BANK HELPLINE (targeted offline by a scammer). The
// shield is on this bank-side call; it reads the scam in the villager's own words.
const SCENARIOS: Scenario[] = [
  {
    id: "pension", label: "Pension / DBT scam", sub: "villager calls the bank, relaying \"share the OTP\"",
    lines: [
      { who: "bank", hi: "दहवानी बैंक हेल्पलाइन, नमस्ते। मैं आपकी क्या मदद करूँ?", en: "Dhwani Bank helpline, hello. How can I help you?" },
      { who: "villager", hi: "बेटा, अभी किसी ने फ़ोन करके कहा कि मेरी पेंशन के छह हज़ार रुपये अटक गए हैं।", en: "Son, someone just called and said my ₹6,000 pension is stuck.", tactics: ["scam_narrative"], addRisk: 24 },
      { who: "villager", hi: "उन्होंने कहा मैं तुरंत एक OTP बता दूँ, वरना पैसा वापस चला जाएगा।", en: "They said I must share an OTP right now, or the money goes back.", tactics: ["high_risk_intent", "duress"], addRisk: 28 },
      { who: "villager", hi: "और कहा किसी को मत बताना। मुझे तो पढ़ना भी नहीं आता, आप बताओ क्या करूँ?", en: "And said don't tell anyone. I can't even read — tell me what to do?", tactics: ["coaching"], addRisk: 22 },
    ],
    warnHi: "सावधान! यह धोखा है। अपना OTP या कोई नंबर किसी को न बताएं। बैंक कभी OTP नहीं माँगता। कॉल काट दें।",
    warnEn: "Warning! This is a scam. Never share your OTP or any number. The bank never asks for an OTP. Hang up.",
  },
  {
    id: "kyc", label: "Fake KYC scam", sub: "villager calls to \"update KYC / share card details\"",
    lines: [
      { who: "bank", hi: "नमस्ते, दहवानी बैंक हेल्पलाइन। बताइए।", en: "Hello, Dhwani Bank helpline. Go ahead." },
      { who: "villager", hi: "साहब, मैसेज आया कि आज मेरा खाता बंद हो जाएगा अगर KYC नहीं हुआ।", en: "Sir, I got a message that my account will be blocked today if KYC isn't done.", tactics: ["scam_narrative", "duress"], addRisk: 26 },
      { who: "villager", hi: "उन्होंने मेरा कार्ड नंबर और OTP माँगा है — मैं दे दूँ क्या?", en: "They've asked for my card number and OTP — should I give it?", tactics: ["high_risk_intent"], addRisk: 30 },
      { who: "villager", hi: "जल्दी करना है, बोले बस दस मिनट बचे हैं।", en: "It's urgent — they said only ten minutes are left.", tactics: ["duress"], addRisk: 18 },
    ],
    warnHi: "सावधान! बैंक कभी कार्ड नंबर या OTP नहीं माँगता। यह धोखा है। किसी को कोई जानकारी न दें।",
    warnEn: "Warning! The bank never asks for your card number or OTP. This is a scam. Share nothing with anyone.",
  },
  {
    id: "arrest", label: "Digital-arrest scam", sub: "villager calls to move money to a \"safe account\"",
    lines: [
      { who: "bank", hi: "दहवानी बैंक हेल्पलाइन, नमस्ते।", en: "Dhwani Bank helpline, hello." },
      { who: "villager", hi: "साहब, पुलिस का फ़ोन आया, बोले मेरे नाम पर केस दर्ज है।", en: "Sir, I got a call from the police saying a case is filed in my name.", tactics: ["scam_narrative", "duress"], addRisk: 26 },
      { who: "villager", hi: "उन्होंने कहा बचना है तो सारा पैसा एक 'सुरक्षित खाते' में डाल दूँ। मुझे वो ट्रांसफर करना है।", en: "They said to be safe I should move all my money to a 'secure account'. I want to make that transfer.", tactics: ["high_risk_intent", "third_party_benefit"], addRisk: 28 },
      { who: "villager", hi: "उन्होंने फ़ोन काटने से और किसी को बताने से मना किया।", en: "They told me not to hang up or tell anyone.", tactics: ["coaching"], addRisk: 18 },
    ],
    warnHi: "रुकिए! पुलिस कभी फ़ोन पर पैसे नहीं माँगती और कोई 'सुरक्षित खाता' नहीं होता। यह धोखा है — पैसा न भेजें।",
    warnEn: "Stop! The police never ask for money on a call, and there is no 'safe account'. This is a scam — do not send money.",
  },
]

const THRESHOLD = 70

function useHindiSpeech() {
  // Web Speech API — offline, no backend. Voices load async; resolve once.
  const ready = useRef(false)
  useEffect(() => {
    if (!("speechSynthesis" in window)) return
    const load = () => { ready.current = window.speechSynthesis.getVoices().length > 0 }
    load()
    window.speechSynthesis.onvoiceschanged = load
  }, [])
  return useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return false
    const synth = window.speechSynthesis
    synth.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = "hi-IN"
    const hi = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith("hi"))
    if (hi) u.voice = hi
    u.rate = 0.9
    synth.speak(u)
    return true
  }, [])
}

function RuralShield() {
  const [scenario, setScenario] = useState<Scenario>(SCENARIOS[0])
  const [phase, setPhase] = useState<"idle" | "playing" | "warned">("idle")
  const [shown, setShown] = useState(0)          // how many lines revealed
  const [risk, setRisk] = useState(0)
  const [tactics, setTactics] = useState<string[]>([])
  const [noVoice, setNoVoice] = useState(false)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const speak = useHindiSpeech()

  const clearTimers = () => { timers.current.forEach(clearTimeout); timers.current = [] }
  useEffect(() => () => { clearTimers(); window.speechSynthesis?.cancel() }, [])

  const reset = useCallback((s: Scenario) => {
    clearTimers(); window.speechSynthesis?.cancel()
    setScenario(s); setPhase("idle"); setShown(0); setRisk(0); setTactics([]); setNoVoice(false)
  }, [])

  const play = useCallback(() => {
    clearTimers(); window.speechSynthesis?.cancel()
    setPhase("playing"); setShown(0); setRisk(0); setTactics([])
    let r = 0
    const seen = new Set<string>()
    scenario.lines.forEach((line, idx) => {
      const t = setTimeout(() => {
        setShown(idx + 1)
        r = Math.min(100, r + (line.addRisk ?? 0))
        setRisk(r)
        for (const tac of line.tactics ?? []) { if (!seen.has(tac)) { seen.add(tac); setTactics([...seen]) } }
        // last line -> fire the intervention
        if (idx === scenario.lines.length - 1) {
          const w = setTimeout(() => {
            setPhase("warned")
            const ok = speak(scenario.warnHi)
            if (!ok) setNoVoice(true)
          }, 900)
          timers.current.push(w)
        }
      }, 1400 * (idx + 1))
      timers.current.push(t)
    })
  }, [scenario, speak])

  const riskColor = risk >= THRESHOLD ? C.threat : risk >= 40 ? C.warn : C.ok

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-6xl mx-auto">
        {/* header */}
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · ग्रामीण कवच</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE SCENARIO</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">A scam warning the customer doesn't have to read</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          The shield sits on the <b style={{ color: C.text }}>bank's own helpline / IVR / Business-Correspondent call</b> — not on the
          scammer's call to the villager. A targeted villager, unable to read an OTP or spot the scam, <b style={{ color: C.text }}>calls the bank</b>
          — confused, or to do what they were told. On that bank line the shield reads the <b style={{ color: C.text }}>coercion in their own
          words</b>, and when the risk spikes it <b style={{ color: C.text }}>speaks a warning back</b> — literacy-free, at the moment of danger.
          Press play (turn your sound on).
        </p>

        {/* scenario picker */}
        <div className="mt-6 flex flex-wrap gap-2">
          {SCENARIOS.map((s) => (
            <button key={s.id} onClick={() => reset(s)} disabled={phase === "playing"}
              className="text-left rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${scenario.id === s.id ? C.warn : C.faint}`, backgroundColor: scenario.id === s.id ? "rgba(245,158,11,0.06)" : "transparent" }}>
              <div className="text-[13px] font-medium">{s.label}</div>
              <div className="text-[11px]" style={{ color: C.muted }}>{s.sub}</div>
            </button>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          {/* the call */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.muted }}>◎ BANK HELPLINE · agent ↔ villager</span>
              <button onClick={play} disabled={phase === "playing"}
                className="rounded-full px-4 py-1.5 text-[12px] font-medium transition-colors disabled:opacity-50"
                style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                {phase === "idle" ? "▶ Play call" : phase === "playing" ? "playing…" : "▶ Replay"}
              </button>
            </div>
            <div className="space-y-3 min-h-[280px]">
              {scenario.lines.slice(0, shown).map((line, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`max-w-[85%] ${line.who === "villager" ? "ml-auto" : ""}`}>
                  <div className="rounded-2xl px-4 py-2.5" style={{
                    backgroundColor: line.who === "villager" ? "rgba(56,189,248,0.06)" : "rgba(94,234,212,0.05)",
                    border: `1px solid ${line.who === "villager" ? "rgba(56,189,248,0.2)" : "rgba(94,234,212,0.2)"}`,
                  }}>
                    <div className="font-mono text-[9px] tracking-wider mb-1" style={{ color: line.who === "villager" ? C.info : C.cyan }}>
                      {line.who === "villager" ? "VILLAGER" : "BANK HELPLINE"}
                    </div>
                    <div className="text-[15px]" style={{ color: C.text }}>{line.hi}</div>
                    <div className="text-[12px] mt-1 italic" style={{ color: C.muted }}>{line.en}</div>
                  </div>
                </motion.div>
              ))}
              {phase === "idle" && <div className="text-[13px]" style={{ color: C.muted }}>Press ▶ Play call to hear the scam unfold and watch the shield intervene.</div>}
            </div>
          </div>

          {/* the shield monitor */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.cyan }}>🛡 SHIELD · listening</span>
            <div className="mt-4">
              <div className="flex items-end justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>APP-FRAUD RISK</span>
                <span className="font-mono font-bold text-[32px] leading-none" style={{ color: riskColor }}>{risk}</span>
              </div>
              <div className="mt-2 h-[6px] w-full rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                <motion.div animate={{ width: `${risk}%` }} transition={{ duration: 0.5 }} style={{ height: "100%", backgroundColor: riskColor }} />
              </div>
            </div>
            <div className="mt-4">
              <div className="font-mono text-[10px] tracking-[0.2em] mb-2" style={{ color: C.muted }}>TACTICS DETECTED · भाषा: हिन्दी</div>
              <div className="flex flex-wrap gap-2 min-h-[30px]">
                {tactics.length === 0 && <span className="text-[12px]" style={{ color: C.muted }}>—</span>}
                <AnimatePresence>
                  {tactics.map((t) => (
                    <motion.span key={t} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                      className="rounded-full px-3 py-1 text-[11px]" style={{ border: `1px solid ${C.warn}`, color: C.warn }}>
                      {TACTIC_LABEL[t] ?? t}
                    </motion.span>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* the intervention */}
            <AnimatePresence>
              {phase === "warned" && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  className="mt-5 rounded-xl p-4" style={{ border: `1px solid ${C.threat}`, backgroundColor: "rgba(255,77,109,0.10)" }}>
                  <div className="flex items-center gap-2">
                    <motion.span animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1, repeat: Infinity }}
                      className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.threat }}>🔊 SHIELD SPEAKS TO CUSTOMER</motion.span>
                  </div>
                  <div className="mt-2 text-[17px] font-semibold" style={{ color: C.text, lineHeight: 1.5 }}>{scenario.warnHi}</div>
                  <div className="mt-2 text-[13px] italic" style={{ color: C.muted }}>{scenario.warnEn}</div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.violet}`, color: C.violet }}>↳ route to human agent</span>
                    <button onClick={() => speak(scenario.warnHi)} className="font-mono text-[11px] ml-auto underline-offset-4 hover:underline" style={{ color: C.cyan }}>🔊 replay warning</button>
                  </div>
                  {noVoice && <div className="mt-2 text-[11px]" style={{ color: C.warn }}>No Hindi voice on this device — the warning shows as text; on a real IVR it's spoken via a Hindi TTS engine.</div>}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* explanation */}
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Why it's literacy-free</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The customer does nothing new — no app, no reading, no PIN. They just talk, and a warning is <b style={{ color: C.text }}>spoken</b> to them in their language. The best security is one a non-literate user never has to operate.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>It's the same engine</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The tactics here map to the <b style={{ color: C.text }}>real APP-fraud detector</b> (Whisper auto-detects Hindi/regional → LLM reads coercion) demonstrated live on the dashboard. Here it drives a vernacular warning instead of just an agent-screen flag.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Where it runs</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>On the bank's IVR / helpline and on <b style={{ color: C.text }}>Business-Correspondent</b> calls — on-prem, no internet needed for detection, works on a ₹1000 feature phone. Reaches customers with <b style={{ color: C.text }}>no app, no literacy, no English</b>.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
