import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Gramin Kavach — the rural intervention. A villager can't read an SMS-OTP, can't
// operate an app, and often can't tell an official-sounding scammer from the real
// bank. So the best protection is one they never have to run: the shield listens
// to the call, reads the COERCION in their own language, and when it spikes it
// SPEAKS a warning back — literacy-free, at the exact second of risk.
//
// This page is an illustrative scenario (clearly labeled): the conversation is
// scripted to real rural scam scripts and the tactics map to the same taxonomy
// the APP-fraud LLM detects live elsewhere. The intervention itself is real — the
// vernacular warning is spoken aloud by the browser (Web Speech API, offline).

export const Route = createFileRoute("/rural")({ component: RuralShield })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Who = "scammer" | "victim"
type Line = { who: Who; hi: string; en: string; tactics?: string[]; addRisk?: number }
type Scenario = { id: string; label: string; sub: string; lines: Line[]; warnHi: string; warnEn: string }

const TACTIC_LABEL: Record<string, string> = {
  scam_narrative: "Scam narrative", duress: "Under duress", high_risk_intent: "High-risk request",
  coaching: "Being coached", third_party_benefit: "Pays a stranger",
}

const SCENARIOS: Scenario[] = [
  {
    id: "pension", label: "Pension / DBT scam", sub: "\"Your pension is stuck — share the OTP\"",
    lines: [
      { who: "scammer", hi: "नमस्ते माताजी, मैं आपके बैंक से बोल रहा हूँ। आपकी पेंशन का ₹6,000 अटक गया है।", en: "Hello mother, I'm calling from your bank. Your ₹6,000 pension is stuck.", tactics: ["scam_narrative"], addRisk: 22 },
      { who: "victim", hi: "हे भगवान! अब मेरा पैसा मिलेगा कि नहीं?", en: "Oh god! Will I get my money or not?", tactics: ["duress"], addRisk: 14 },
      { who: "scammer", hi: "मिलेगा, पर अभी करना होगा। आपके फ़ोन पर एक नंबर आया है, वो मुझे बता दीजिए।", en: "You will, but do it now. A number came to your phone — tell it to me.", tactics: ["high_risk_intent", "duress"], addRisk: 26 },
      { who: "victim", hi: "मुझे तो पढ़ना नहीं आता बेटा…", en: "But I can't read, son…", addRisk: 4 },
      { who: "scammer", hi: "कोई बात नहीं, मैं बताता हूँ क्या दबाना है। और ये बात किसी को मत बताना, वरना पेंशन बंद हो जाएगी।", en: "No matter, I'll tell you what to press. And don't tell anyone, or the pension stops.", tactics: ["coaching", "duress"], addRisk: 22 },
    ],
    warnHi: "सावधान! यह कॉल धोखा हो सकती है। अपना OTP या कोई नंबर किसी को न बताएं। बैंक कभी OTP नहीं माँगता। कॉल काट दें।",
    warnEn: "Warning! This call may be a scam. Never share your OTP or any number. The bank never asks for an OTP. Hang up.",
  },
  {
    id: "kyc", label: "Fake KYC scam", sub: "\"Your account will be blocked today\"",
    lines: [
      { who: "scammer", hi: "सर, आपका खाता आज बंद हो जाएगा अगर KYC अपडेट नहीं हुआ।", en: "Sir, your account will be blocked today if KYC isn't updated.", tactics: ["scam_narrative", "duress"], addRisk: 26 },
      { who: "victim", hi: "अरे नहीं! क्या करना पड़ेगा साहब?", en: "Oh no! What do I have to do, sir?", tactics: ["duress"], addRisk: 12 },
      { who: "scammer", hi: "बस अपना कार्ड नंबर और OTP मुझे बता दीजिए, मैं अपडेट कर देता हूँ।", en: "Just tell me your card number and OTP, I'll update it.", tactics: ["high_risk_intent"], addRisk: 28 },
      { who: "scammer", hi: "जल्दी कीजिए, सिर्फ़ दस मिनट बचे हैं।", en: "Hurry, only ten minutes left.", tactics: ["duress"], addRisk: 20 },
    ],
    warnHi: "सावधान! बैंक कभी कार्ड नंबर या OTP फ़ोन पर नहीं माँगता। यह धोखा है। कोई जानकारी न दें और कॉल काट दें।",
    warnEn: "Warning! The bank never asks for your card number or OTP on a call. This is a scam. Share nothing and hang up.",
  },
  {
    id: "arrest", label: "Digital-arrest scam", sub: "\"Police — move money to a safe account\"",
    lines: [
      { who: "scammer", hi: "मैं पुलिस से बोल रहा हूँ। आपके नाम से एक केस दर्ज हुआ है।", en: "I'm from the police. A case has been filed in your name.", tactics: ["scam_narrative", "duress"], addRisk: 26 },
      { who: "victim", hi: "मैंने तो कुछ नहीं किया साहब!", en: "But I've done nothing, sir!", tactics: ["duress"], addRisk: 14 },
      { who: "scammer", hi: "बचना है तो सारा पैसा इस सुरक्षित खाते में डाल दीजिए, जाँच के बाद वापस मिल जाएगा।", en: "To be safe, move all your money to this secure account — you'll get it back after the enquiry.", tactics: ["high_risk_intent", "third_party_benefit", "scam_narrative"], addRisk: 26 },
      { who: "scammer", hi: "फ़ोन मत काटिए और किसी को मत बताइए।", en: "Don't hang up, and don't tell anyone.", tactics: ["coaching"], addRisk: 18 },
    ],
    warnHi: "सावधान! पुलिस कभी फ़ोन पर पैसे नहीं माँगती और कोई 'सुरक्षित खाता' नहीं होता। यह धोखा है। तुरंत कॉल काटें।",
    warnEn: "Warning! The police never ask for money on a call, and there is no 'safe account'. This is a scam. Hang up now.",
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
          A villager can't read an SMS-OTP, can't run an app, and can't always tell an official-sounding scammer
          from the real bank. So the shield listens to the call, reads the <b style={{ color: C.text }}>coercion in their own language</b>,
          and when the risk spikes it <b style={{ color: C.text }}>speaks a warning back</b> — literacy-free, at the exact
          second of danger. Press play (turn your sound on).
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
              <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.muted }}>◎ LIVE CALL · caller ↔ villager</span>
              <button onClick={play} disabled={phase === "playing"}
                className="rounded-full px-4 py-1.5 text-[12px] font-medium transition-colors disabled:opacity-50"
                style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                {phase === "idle" ? "▶ Play call" : phase === "playing" ? "playing…" : "▶ Replay"}
              </button>
            </div>
            <div className="space-y-3 min-h-[280px]">
              {scenario.lines.slice(0, shown).map((line, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`max-w-[85%] ${line.who === "victim" ? "ml-auto" : ""}`}>
                  <div className="rounded-2xl px-4 py-2.5" style={{
                    backgroundColor: line.who === "scammer" ? "rgba(255,77,109,0.08)" : "rgba(56,189,248,0.06)",
                    border: `1px solid ${line.who === "scammer" ? "rgba(255,77,109,0.25)" : "rgba(56,189,248,0.2)"}`,
                  }}>
                    <div className="font-mono text-[9px] tracking-wider mb-1" style={{ color: line.who === "scammer" ? C.threat : C.info }}>
                      {line.who === "scammer" ? "CALLER (scammer)" : "VILLAGER"}
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
