import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Beyond the contact centre #1 — deepfake-executive protection on the bank's OWN
// money movements. High-value RTGS/SWIFT/treasury transfers are confirmed by a
// voice CALLBACK to an authorising officer — now spoofable by a cloned executive
// voice (the Arup case: US$25M to a deepfake CFO). The bank runs the shield on
// that callback: voiceprint (is it the enrolled officer) + synthetic-voice check
// (is it a live human or a clone). Protects the bank's vault, not just customers.
//
// Illustrative scenario (labeled); numbers from the real ECAPA/deepfake engine.

export const Route = createFileRoute("/treasury")({ component: Treasury })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }
const ACCEPT = 0.40
const inr = (n: number) => "₹" + n.toLocaleString("en-IN")

type Scen = { id: string; label: string; sub: string; cosine: number; deepfakeRed: boolean; ok: boolean; reason: string; note: string; color: string }

const SCENS: Scen[] = [
  { id: "genuine", label: "The real CFO authorises", sub: "Mr. Rao confirms the wire by voice", cosine: 0.83, deepfakeRed: false, ok: true, color: "#22C55E",
    reason: "Voice matches the enrolled authorising officer, and it's a live human.", note: "The callback does its job — a second factor that binds the authorisation to the real person." },
  { id: "clone", label: "Deepfake of the CFO", sub: "voice-BEC: a cloned Mr. Rao 'authorises' it", cosine: 0.70, deepfakeRed: true, ok: false, color: "#FF4D6D",
    reason: "Voiceprint alone would PASS (0.70 ≥ 0.40) — the synthetic-voice check flags the clone.", note: "This is the Arup-style attack: a cloned executive voice authorising a wire. The voiceprint can be partly fooled — the deepfake detector is why the money doesn't leave." },
  { id: "impostor", label: "An impostor officer", sub: "someone else tries to authorise", cosine: 0.16, deepfakeRed: false, ok: false, color: "#FF4D6D",
    reason: "Voice does not match the enrolled officer — authorisation refused.", note: "A stolen phone or a colleague can't stand in for the authorising officer's own voice." },
]

const AMOUNT = 50000000

function Treasury() {
  const [scen, setScen] = useState<Scen>(SCENS[0])
  const [phase, setPhase] = useState<"idle" | "checking" | "done">("idle")
  const [cos, setCos] = useState(0)

  const run = useCallback(() => {
    setPhase("checking"); setCos(0)
    setTimeout(() => { setCos(scen.cosine); setPhase("done") }, 1100)
  }, [scen])
  const pick = (s: Scen) => { setScen(s); setPhase("idle"); setCos(0) }
  const cosColor = cos >= ACCEPT ? (scen.deepfakeRed ? C.warn : C.ok) : C.threat

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · TREASURY CALLBACK</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE · BEYOND THE CONTACT CENTRE</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">A cloned executive can't authorise your wire</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          High-value transfers are confirmed by a <b style={{ color: C.text }}>voice callback</b> to an authorising officer — and that voice is now
          clonable (the Arup case: <b style={{ color: C.text }}>US$25M</b> lost to a deepfake CFO). The bank runs the shield on its own callback:
          voiceprint <b style={{ color: C.text }}>+</b> synthetic-voice check. This protects the <b style={{ color: C.text }}>bank's own money</b>.
        </p>

        {/* the pending transfer */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>PENDING RTGS AUTHORISATION</div>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <span className="font-mono text-[30px] font-bold">{inr(AMOUNT)}</span>
            <span className="text-[13px]" style={{ color: C.warn }}>→ new counterparty · off-cycle · awaiting voice authorisation from CFO (M. Rao, voiceprint enrolled)</span>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* who's on the callback */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>WHO'S ON THE CALLBACK?</div>
            <div className="space-y-2">
              {SCENS.map((s) => (
                <button key={s.id} onClick={() => pick(s)} disabled={phase === "checking"}
                  className="w-full text-left rounded-xl px-4 py-3 transition-colors disabled:opacity-50"
                  style={{ border: `1px solid ${scen.id === s.id ? s.color : C.faint}`, backgroundColor: scen.id === s.id ? "rgba(255,255,255,0.03)" : "transparent" }}>
                  <div className="text-[14px] font-medium">{s.label}</div>
                  <div className="text-[12px]" style={{ color: C.muted }}>{s.sub}</div>
                </button>
              ))}
            </div>
            <button onClick={run} disabled={phase === "checking"}
              className="mt-4 w-full rounded-xl py-3 font-mono text-[13px] font-bold tracking-wider transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
              {phase === "checking" ? "VERIFYING VOICE…" : "▶ VERIFY & AUTHORISE"}
            </button>
          </div>

          {/* verdict */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 AUTHORISATION CHECK</div>
            <div>
              <div className="flex items-end justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>OFFICER VOICEPRINT (cosine)</span>
                <span className="font-mono font-bold text-[28px] leading-none" style={{ color: phase === "done" ? cosColor : C.muted }}>{phase === "done" ? cos.toFixed(2) : "—"}</span>
              </div>
              <div className="relative mt-2 h-[8px] w-full rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                <motion.div animate={{ width: `${cos * 100}%` }} transition={{ duration: 0.8 }} style={{ height: "100%", backgroundColor: cosColor }} />
                <div className="absolute top-0 h-full" style={{ left: `${ACCEPT * 100}%`, width: 2, backgroundColor: C.text, opacity: 0.5 }} />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>SYNTHETIC-VOICE CHECK</span>
              {phase === "done"
                ? <span className="font-mono text-[11px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${scen.deepfakeRed ? C.threat : C.ok}`, color: scen.deepfakeRed ? C.threat : C.ok }}>{scen.deepfakeRed ? "RED · clone detected" : "GREEN · live human"}</span>
                : <span className="font-mono text-[11px]" style={{ color: C.muted }}>—</span>}
            </div>
            <AnimatePresence mode="wait">
              {phase === "done" && (
                <motion.div key={scen.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="mt-5 rounded-xl px-4 py-4 text-center" style={{ border: `1px solid ${scen.ok ? C.ok : C.threat}`, backgroundColor: scen.ok ? "rgba(34,197,94,0.08)" : "rgba(255,77,109,0.10)" }}>
                  <div className="font-mono font-bold text-[19px] tracking-wider" style={{ color: scen.ok ? C.ok : C.threat }}>
                    {scen.ok ? "✓ WIRE AUTHORISED" : "✗ AUTHORISATION BLOCKED"}
                  </div>
                  <div className="mt-1.5 text-[13px]" style={{ color: C.text }}>{scen.ok ? `${inr(AMOUNT)} released.` : `${inr(AMOUNT)} held. ${scen.reason}`}</div>
                </motion.div>
              )}
              {phase === "idle" && <div className="mt-5 text-[13px]" style={{ color: C.muted }}>Pick who's on the callback, then verify.</div>}
            </AnimatePresence>
          </div>
        </div>

        {/* explanation */}
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>The board-level threat</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Deepfake-executive fraud (voice/video BEC) has already moved eight-figure sums. It attacks the bank's <b style={{ color: C.text }}>own</b> money-movement, not a customer account.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Why the voiceprint isn't enough</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>A good clone can partly pass a 1:1 voiceprint (0.70 here). The <b style={{ color: C.text }}>synthetic-voice detector</b> alongside it is what stops the wire.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Same engine, new channel</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Nothing new to build — the ECAPA voiceprint + deepfake detector, pointed at the <b style={{ color: C.text }}>treasury callback</b> instead of the contact centre.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
