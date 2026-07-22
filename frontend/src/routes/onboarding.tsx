import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Beyond the contact centre #3 — secure the front door. Remote video-KYC / V-CIP
// onboarding is being defeated by deepfakes (synthetic faces + voices opening mule
// accounts). Three things in one, on the bank's own onboarding call:
//   1. synthetic-voice / liveness check  -> block deepfake account-opening
//   2. enrol the voiceprint              -> a lifelong auth factor for every future call
//   3. voiceprint-reuse check            -> the same voice opening many "different"
//                                           accounts = a mule / synthetic-identity ring
//
// Illustrative scenario (labeled); numbers from the real ECAPA/deepfake engine.

export const Route = createFileRoute("/onboarding")({ component: Onboarding })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Scen = { id: string; label: string; sub: string; deepfakeRed: boolean; mule: number; ok: boolean; verdict: string; reason: string; note: string; color: string }

const SCENS: Scen[] = [
  { id: "genuine", label: "A genuine new customer", sub: "Aarti, opening her first account", deepfakeRed: false, mule: 0, ok: true, color: "#22C55E", verdict: "✓ ENROLLED · ACCOUNT OPENED",
    reason: "Live human, and this voice matches no existing account. Voiceprint stored.", note: "The onboarding moment mints a lifelong voice identity — the factor that secures every future call, with nothing for the customer to remember." },
  { id: "deepfake", label: "A deepfake onboarding", sub: "a synthetic face + voice opening an account", deepfakeRed: true, mule: 0, ok: false, color: "#FF4D6D", verdict: "✗ BLOCKED · SYNTHETIC",
    reason: "Synthetic-voice detected — this isn't a live person. Onboarding refused.", note: "Deepfake KYC is how synthetic identities and mule accounts are minted at scale. Blocking it at the door stops the fraud before an account exists." },
  { id: "mule", label: "A mule / synthetic identity", sub: "'different' customer, same voice as 6 others", deepfakeRed: false, mule: 6, ok: false, color: "#F59E0B", verdict: "✗ BLOCKED · MULE RING",
    reason: "This voice already opened 6 other 'different' accounts — a mule / synthetic-identity ring.", note: "Voiceprint-reuse across onboardings exposes the network a single application review never could — one operator behind many identities." },
]

function Onboarding() {
  const [scen, setScen] = useState<Scen>(SCENS[0])
  const [phase, setPhase] = useState<"idle" | "checking" | "done">("idle")

  const run = useCallback(() => { setPhase("checking"); setTimeout(() => setPhase("done"), 1100) }, [])
  const pick = (s: Scen) => { setScen(s); setPhase("idle") }

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · VIDEO-KYC ONBOARDING</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE · BEYOND THE CONTACT CENTRE</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">Secure the front door — and mint a lifelong voice identity</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          Remote onboarding (V-CIP) is being defeated by deepfakes opening mule accounts. On the onboarding call the shield does three things:
          <b style={{ color: C.text }}> block a deepfake</b>, <b style={{ color: C.text }}>enrol the voiceprint</b> (a factor for every future call), and check for
          <b style={{ color: C.text }}> voiceprint reuse</b> — the same voice behind many "different" identities = a mule ring.
        </p>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>WHO'S ON THE ONBOARDING CALL?</div>
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
              {phase === "checking" ? "SCREENING…" : "▶ SCREEN & ENROL"}
            </button>
          </div>

          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 ONBOARDING SCREEN</div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>SYNTHETIC-VOICE / LIVENESS</span>
                {phase === "done"
                  ? <span className="font-mono text-[11px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${scen.deepfakeRed ? C.threat : C.ok}`, color: scen.deepfakeRed ? C.threat : C.ok }}>{scen.deepfakeRed ? "RED · synthetic" : "GREEN · live human"}</span>
                  : <span className="font-mono text-[11px]" style={{ color: C.muted }}>—</span>}
              </div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>VOICEPRINT REUSE (mule check)</span>
                {phase === "done"
                  ? <span className="font-mono text-[11px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${scen.mule ? C.threat : C.ok}`, color: scen.mule ? C.threat : C.ok }}>{scen.mule ? `${scen.mule} other accounts` : "unique · 0 matches"}</span>
                  : <span className="font-mono text-[11px]" style={{ color: C.muted }}>—</span>}
              </div>
            </div>
            <AnimatePresence mode="wait">
              {phase === "done" && (
                <motion.div key={scen.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="mt-5 rounded-xl px-4 py-4" style={{ border: `1px solid ${scen.color}`, backgroundColor: `${scen.color}14` }}>
                  <div className="font-mono font-bold text-[18px] tracking-wider" style={{ color: scen.color }}>{scen.verdict}</div>
                  <div className="mt-1.5 text-[13px]" style={{ color: C.text }}>{scen.reason}</div>
                </motion.div>
              )}
              {phase === "idle" && <div className="mt-5 text-[13px]" style={{ color: C.muted }}>Pick who's onboarding, then screen &amp; enrol.</div>}
            </AnimatePresence>
          </div>
        </div>

        {/* takeaway */}
        <AnimatePresence>
          {phase === "done" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="mt-6 rounded-xl px-5 py-4" style={{ border: `1px solid ${C.faint}`, backgroundColor: C.surface }}>
              <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.cyan }}>WHY IT MATTERS</span>
              <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>{scen.note}</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Block deepfake KYC</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Synthetic faces/voices open mule accounts at scale. Liveness at the door stops the fraud before an account even exists.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Mint a lifelong identity</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The enrolled voiceprint secures every future call — the auth factor born at onboarding, nothing to remember.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Expose mule networks</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>One voice behind six identities is invisible to per-application review — obvious to voiceprint correlation.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
