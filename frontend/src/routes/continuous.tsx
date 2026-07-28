import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Beyond the contact centre #4 — continuous passive auth + mid-call takeover.
// Today auth is a GATE at the start of a call. Instead, run the voiceprint the
// WHOLE call and watch for the speaker CHANGING: the genuine customer
// authenticates, then hands the phone to a "helper" (a coached third party or the
// fraudster) to do the transaction. Detecting that hand-off mid-call is a security
// primitive that doesn't exist today — and it's the core APP-fraud mechanic.
//
// Illustrative scenario (labeled): per-2s-window voiceprint match vs the enrolled
// customer; a sustained drop = a different speaker took over.

export const Route = createFileRoute("/continuous")({ component: Continuous })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }
const ACCEPT = 0.4

type Scen = { id: string; label: string; sub: string; track: number[]; takeoverAt: number | null }

const N = 15
const hi = () => 0.74 + Math.random() * 0.12
const lo = () => 0.14 + Math.random() * 0.12
const genuine = Array.from({ length: N }, hi)
const takeover = Array.from({ length: N }, (_, i) => (i < 8 ? hi() : lo()))

const SCENS: Scen[] = [
  { id: "genuine", label: "Genuine call", sub: "the same customer, start to finish", track: genuine, takeoverAt: null },
  { id: "takeover", label: "Mid-call takeover", sub: "customer authenticates, then hands the phone to a 'helper'", track: takeover, takeoverAt: 8 },
]

function Continuous() {
  const [scen, setScen] = useState<Scen>(SCENS[0])
  const [i, setI] = useState(-1)             // current window index
  const [playing, setPlaying] = useState(false)
  const [alerted, setAlerted] = useState(false)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const stop = () => { if (timer.current) clearInterval(timer.current); timer.current = null; setPlaying(false) }
  useEffect(() => () => stop(), [])

  const play = useCallback(() => {
    stop(); setI(-1); setAlerted(false); setPlaying(true)
    let k = -1
    timer.current = setInterval(() => {
      k += 1
      setI(k)
      if (scen.takeoverAt !== null && k >= scen.takeoverAt) setAlerted(true)
      if (k >= N - 1) stop()
    }, 420)
  }, [scen])

  const pick = (s: Scen) => { stop(); setScen(s); setI(-1); setAlerted(false) }
  const cur = i >= 0 ? scen.track[i] : null
  const curColor = cur === null ? C.muted : cur >= ACCEPT ? C.ok : C.threat

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · CONTINUOUS AUTH</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE · BEYOND THE CONTACT CENTRE</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">Verify the whole call — and catch the hand-off</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          Auth today is a gate at the <i>start</i> of a call. Instead, run the voiceprint <b style={{ color: C.text }}>continuously</b>: the customer
          passes, then hands the phone to a "helper" to do the transaction. That <b style={{ color: C.text }}>speaker change</b> is exactly the
          APP-fraud mechanic — and detecting it mid-call is a security primitive that doesn't exist today.
        </p>

        {/* controls */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <div className="flex rounded-full overflow-hidden" style={{ border: `1px solid ${C.faint}` }}>
            {SCENS.map((s) => (
              <button key={s.id} onClick={() => pick(s)} disabled={playing}
                className="px-4 py-1.5 text-[12px] font-medium transition-colors disabled:opacity-40"
                style={{ backgroundColor: scen.id === s.id ? C.cyan : "transparent", color: scen.id === s.id ? "#0A0B0F" : C.muted }}>
                {s.label}
              </button>
            ))}
          </div>
          <span className="text-[12px]" style={{ color: C.muted }}>{scen.sub}</span>
          <button onClick={play} disabled={playing}
            className="ml-auto rounded-full px-5 py-2 text-[12px] font-medium transition-colors disabled:opacity-40"
            style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
            {playing ? "▶ live…" : "▶ Play the call"}
          </button>
        </div>

        {/* live match track */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="flex items-center justify-between mb-3">
            <span className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.muted }}>VOICEPRINT MATCH vs ENROLLED CUSTOMER · per 2s window</span>
            <span className="font-mono text-[12px]" style={{ color: curColor }}>{cur === null ? "—" : `now ${cur.toFixed(2)}`}</span>
          </div>
          <div className="flex items-end gap-1.5" style={{ height: 120 }}>
            {scen.track.map((v, k) => {
              const shown = k <= i
              const isTakeover = scen.takeoverAt !== null && k === scen.takeoverAt
              const color = !shown ? "rgba(255,255,255,0.05)" : v >= ACCEPT ? C.ok : C.threat
              return (
                <div key={k} className="flex-1 flex flex-col justify-end items-center" style={{ height: "100%" }}>
                  <div style={{ width: "100%", height: `${(shown ? v : 0.04) * 100}%`, backgroundColor: color, borderRadius: "3px 3px 0 0", transition: "height .25s, background-color .25s", position: "relative" }}>
                    {shown && isTakeover && <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[11px]" style={{ color: C.threat }}>⚠</span>}
                  </div>
                </div>
              )
            })}
          </div>
          {/* accept line label */}
          <div className="font-mono text-[10px] mt-1" style={{ color: C.muted }}>green ≥ {ACCEPT.toFixed(2)} match · red = a different speaker</div>
        </div>

        {/* status / alert */}
        <AnimatePresence mode="wait">
          {alerted ? (
            <motion.div key="alert" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="mt-5 rounded-xl px-5 py-4 flex flex-wrap items-center gap-3" style={{ border: `1px solid ${C.threat}`, backgroundColor: "rgba(255,77,109,0.10)" }}>
              <span className="font-mono font-bold text-[15px] tracking-wider" style={{ color: C.threat }}>⚠ SPEAKER CHANGED · TAKEOVER</span>
              <span className="text-[13px]" style={{ color: C.text }}>The verified customer is no longer the one speaking — the phone was handed off mid-call. Freeze the transaction, re-verify.</span>
            </motion.div>
          ) : i >= N - 1 ? (
            <motion.div key="ok" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="mt-5 rounded-xl px-5 py-4 flex items-center gap-3" style={{ border: `1px solid ${C.ok}`, backgroundColor: "rgba(34,197,94,0.08)" }}>
              <span className="font-mono font-bold text-[15px] tracking-wider" style={{ color: C.ok }}>✓ ONE SPEAKER THROUGHOUT</span>
              <span className="text-[13px]" style={{ color: C.text }}>The same verified customer spoke start to finish — no hand-off. Transaction can proceed.</span>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>A gate isn't enough</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Verifying only at the start means whoever takes the phone <i>after</i> inherits the trust. Continuous auth removes that blind spot.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Catches the real mechanic</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>"Let me put my nephew on, he'll do it" — the coached hand-off is how a huge share of APP-fraud actually completes.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Free from the same pass</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The voiceprint is already computed per window for detection — comparing consecutive windows to the enrolled print costs nothing extra.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
