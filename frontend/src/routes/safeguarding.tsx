import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Beyond the contact centre #5 — vulnerable-customer & duress safeguarding.
// Beyond APP-fraud: on a bank call, detect elder financial abuse (a caregiver
// coercing an elderly customer), coercion/duress (someone in the room), or genuine
// distress — from the coaching + stress signals in the conversation — and route to
// a SAFEGUARDING team, not a cold fraud-block. Regulators are moving hard on
// vulnerable-customer duty; this makes the bank a guardian, not just a gatekeeper.
//
// Illustrative scenario (labeled); the coercion/coaching signals map to the same
// APP-fraud engine, with a safeguarding outcome instead of a block.

export const Route = createFileRoute("/safeguarding")({ component: Safeguarding })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Who = "bank" | "customer"
type Line = { who: Who; text: string; sub?: string; signals?: string[]; addRisk?: number }
type Scen = { id: string; label: string; sub: string; lines: Line[] }

const SIGNAL_LABEL: Record<string, string> = {
  coaching: "Being coached", distress: "Confusion / distress", dependency: "Financial dependency",
  life_savings: "Life-savings at risk", duress: "Under duress",
}

const SCENS: Scen[] = [
  {
    id: "elder", label: "Elder financial abuse", sub: "an elderly customer coached to move savings",
    lines: [
      { who: "bank", text: "Thank you for calling the bank. How can I help you today?" },
      { who: "customer", text: "I… I need to transfer my fixed deposit. My nephew is here, he says I must do it today.", sub: "elderly caller · a second voice prompting in the background", signals: ["coaching", "dependency"], addRisk: 26 },
      { who: "customer", text: "He's telling me what to press… I don't really understand why, but he says it's urgent.", signals: ["distress", "coaching"], addRisk: 26 },
      { who: "customer", text: "It's all my savings. He'll look after the money for me, he said.", signals: ["life_savings"], addRisk: 24 },
    ],
  },
  {
    id: "duress", label: "Customer under duress", sub: "the 'right' words, but coerced in the room",
    lines: [
      { who: "bank", text: "For security, is everything alright — are you making this transfer freely?" },
      { who: "customer", text: "Yes… yes, everything is fine. Please just do it quickly.", sub: "tense, hurried; hesitations; a voice murmuring nearby", signals: ["duress", "distress"], addRisk: 30 },
      { who: "customer", text: "I can't really talk right now. Just… send it, please.", signals: ["duress", "coaching"], addRisk: 30 },
    ],
  },
]

const THRESHOLD = 60

function Safeguarding() {
  const [scen, setScen] = useState<Scen>(SCENS[0])
  const [phase, setPhase] = useState<"idle" | "playing" | "flagged">("idle")
  const [shown, setShown] = useState(0)
  const [risk, setRisk] = useState(0)
  const [signals, setSignals] = useState<string[]>([])
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  const clear = () => { timers.current.forEach(clearTimeout); timers.current = [] }
  const reset = (s: Scen) => { clear(); setScen(s); setPhase("idle"); setShown(0); setRisk(0); setSignals([]) }

  const play = useCallback(() => {
    clear(); setPhase("playing"); setShown(0); setRisk(0); setSignals([])
    let r = 0; const seen = new Set<string>()
    scen.lines.forEach((line, idx) => {
      timers.current.push(setTimeout(() => {
        setShown(idx + 1)
        r = Math.min(100, r + (line.addRisk ?? 0)); setRisk(r)
        for (const s of line.signals ?? []) if (!seen.has(s)) { seen.add(s); setSignals([...seen]) }
        if (idx === scen.lines.length - 1) timers.current.push(setTimeout(() => setPhase("flagged"), 800))
      }, 1500 * (idx + 1)))
    })
  }, [scen])

  const riskColor = risk >= THRESHOLD ? C.violet : risk >= 30 ? C.warn : C.ok

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · SAFEGUARDING</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE · BEYOND THE CONTACT CENTRE</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">A guardian, not just a gatekeeper</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          Beyond fraud: on a bank call, the shield can hear <b style={{ color: C.text }}>elder abuse, coercion, or genuine distress</b> in the
          conversation — and route to a <b style={{ color: C.text }}>safeguarding team</b> for a welfare check, not a cold block that would frighten
          a vulnerable customer. A rising regulatory duty, and a reputation nobody else offers.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {SCENS.map((s) => (
            <button key={s.id} onClick={() => reset(s)} disabled={phase === "playing"}
              className="text-left rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${scen.id === s.id ? C.violet : C.faint}`, backgroundColor: scen.id === s.id ? "rgba(167,139,250,0.06)" : "transparent" }}>
              <div className="text-[13px] font-medium">{s.label}</div>
              <div className="text-[11px]" style={{ color: C.muted }}>{s.sub}</div>
            </button>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          {/* the call */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.muted }}>◎ BANK CALL · agent ↔ customer</span>
              <button onClick={play} disabled={phase === "playing"}
                className="rounded-full px-4 py-1.5 text-[12px] font-medium transition-colors disabled:opacity-50"
                style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                {phase === "idle" ? "▶ Play call" : phase === "playing" ? "playing…" : "▶ Replay"}
              </button>
            </div>
            <div className="space-y-3 min-h-[240px]">
              {scen.lines.slice(0, shown).map((line, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`max-w-[88%] ${line.who === "customer" ? "ml-auto" : ""}`}>
                  <div className="rounded-2xl px-4 py-2.5" style={{ backgroundColor: line.who === "customer" ? "rgba(167,139,250,0.06)" : "rgba(94,234,212,0.05)", border: `1px solid ${line.who === "customer" ? "rgba(167,139,250,0.25)" : "rgba(94,234,212,0.2)"}` }}>
                    <div className="font-mono text-[9px] tracking-wider mb-1" style={{ color: line.who === "customer" ? C.violet : C.cyan }}>{line.who === "customer" ? "CUSTOMER" : "BANK AGENT"}</div>
                    <div className="text-[14px]" style={{ color: C.text }}>{line.text}</div>
                    {line.sub && <div className="text-[11px] mt-1 italic" style={{ color: C.muted }}>{line.sub}</div>}
                  </div>
                </motion.div>
              ))}
              {phase === "idle" && <div className="text-[13px]" style={{ color: C.muted }}>Press ▶ Play call to watch the shield hear a vulnerable customer.</div>}
            </div>
          </div>

          {/* monitor */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.cyan }}>🛡 SHIELD · listening for harm</span>
            <div className="mt-4">
              <div className="flex items-end justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>VULNERABILITY &amp; COERCION</span>
                <span className="font-mono font-bold text-[30px] leading-none" style={{ color: riskColor }}>{risk}</span>
              </div>
              <div className="mt-2 h-[6px] w-full rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                <motion.div animate={{ width: `${risk}%` }} transition={{ duration: 0.5 }} style={{ height: "100%", backgroundColor: riskColor }} />
              </div>
            </div>
            <div className="mt-4">
              <div className="font-mono text-[10px] tracking-[0.2em] mb-2" style={{ color: C.muted }}>SIGNALS DETECTED</div>
              <div className="flex flex-wrap gap-2 min-h-[30px]">
                {signals.length === 0 && <span className="text-[12px]" style={{ color: C.muted }}>—</span>}
                <AnimatePresence>
                  {signals.map((s) => (
                    <motion.span key={s} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                      className="rounded-full px-3 py-1 text-[11px]" style={{ border: `1px solid ${C.violet}`, color: C.violet }}>
                      {SIGNAL_LABEL[s] ?? s}
                    </motion.span>
                  ))}
                </AnimatePresence>
              </div>
            </div>
            <AnimatePresence>
              {phase === "flagged" && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  className="mt-5 rounded-xl p-4" style={{ border: `1px solid ${C.violet}`, backgroundColor: "rgba(167,139,250,0.10)" }}>
                  <div className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.violet }}>↳ ROUTE TO SAFEGUARDING TEAM</div>
                  <div className="mt-2 text-[13px]" style={{ color: C.text, lineHeight: 1.5 }}>Held for a <b>welfare check</b> by a trained agent + a cooling-off — not a cold block. The customer is protected without being frightened or accused.</div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>A regulatory duty</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Vulnerable-customer protection is a rising expectation. This operationalises it — detectable, logged, and acted on in real time.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Care, not a cold block</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>A vulnerable customer gets a welfare check and a human — not a hard decline that distresses them or tips off an abuser.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Same engine, kinder outcome</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The coaching/duress signals come from the same APP-fraud layer — routed to safeguarding instead of fraud when the driver is harm, not theft.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
