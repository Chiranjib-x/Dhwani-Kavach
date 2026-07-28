import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Beyond the contact centre #2 — the IT-helpdesk / privileged-access firewall.
// The #1 way banks actually get breached is social-engineering the helpdesk: an
// attacker calls posing as an employee to reset MFA or unlock privileged access
// (MGM/Caesars). The bank runs the shield on its OWN internal helpdesk calls:
// voiceprint (is it the enrolled employee) + liveness (a live human, not a clone/
// recording). Points the customer-fraud tech at the bank's own attack surface.
//
// Illustrative scenario (labeled); numbers from the real ECAPA/deepfake engine.

export const Route = createFileRoute("/helpdesk")({ component: Helpdesk })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }
const ACCEPT = 0.40

type Scen = { id: string; label: string; sub: string; cosine: number; deepfakeRed: boolean; ok: boolean; reason: string; note: string; color: string }

const SCENS: Scen[] = [
  { id: "genuine", label: "The real admin", sub: "Priya (DBA) calls to reset her own MFA", cosine: 0.84, deepfakeRed: false, ok: true, color: "#22C55E",
    reason: "Voice matches the enrolled employee, and it's live.", note: "The reset proceeds — bound to the person, not just to knowing her employee ID and the answer to a security question." },
  { id: "social", label: "A social engineer", sub: "\"Hi, I'm Priya, I'm locked out — reset my MFA now\"", cosine: 0.13, deepfakeRed: false, ok: false, color: "#FF4D6D",
    reason: "Voice does not match the enrolled employee — VOICE_MISMATCH. Reset refused.", note: "This is the MGM/Caesars breach pattern: a caller who knows the employee's details but isn't them. Knowledge is stealable; the voice isn't." },
  { id: "clone", label: "A cloned employee voice", sub: "attacker plays a synthetic clone of Priya", cosine: 0.72, deepfakeRed: true, ok: false, color: "#F59E0B",
    reason: "Voiceprint alone would PASS (0.72 ≥ 0.40) — the synthetic-voice check flags the clone.", note: "A recording/clone of a real employee is caught by the deepfake detector — the reason the voiceprint runs with a liveness check, not alone." },
]

function Helpdesk() {
  const [scen, setScen] = useState<Scen>(SCENS[0])
  const [phase, setPhase] = useState<"idle" | "checking" | "done">("idle")
  const [cos, setCos] = useState(0)

  const run = useCallback(() => { setPhase("checking"); setCos(0); setTimeout(() => { setCos(scen.cosine); setPhase("done") }, 1100) }, [scen])
  const pick = (s: Scen) => { setScen(s); setPhase("idle"); setCos(0) }
  const cosColor = cos >= ACCEPT ? (scen.deepfakeRed ? C.warn : C.ok) : C.threat

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · IT HELPDESK</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE · BEYOND THE CONTACT CENTRE</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">Is the "employee" calling the helpdesk really them?</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          The #1 way banks get breached today is <b style={{ color: C.text }}>social-engineering the IT helpdesk</b> — a caller posing as an
          employee to reset MFA or unlock privileged access. The bank runs the shield on its <b style={{ color: C.text }}>own internal</b> helpdesk
          calls: voiceprint <b style={{ color: C.text }}>+</b> liveness. The customer-fraud tech, pointed at the bank's own attack surface — its people.
        </p>

        {/* the privileged request */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>PRIVILEGED REQUEST</div>
          <div className="mt-1 text-[15px]" style={{ color: C.text }}>Reset MFA + unlock <b>production database admin</b> access for <b>Priya S.</b> <span style={{ color: C.warn }}>(voiceprint enrolled)</span></div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>WHO'S CALLING THE HELPDESK?</div>
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
              {phase === "checking" ? "VERIFYING VOICE…" : "▶ VERIFY BEFORE RESET"}
            </button>
          </div>

          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 EMPLOYEE VERIFICATION</div>
            <div>
              <div className="flex items-end justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>EMPLOYEE VOICEPRINT (cosine)</span>
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
                  className="mt-5 rounded-xl px-4 py-4" style={{ border: `1px solid ${scen.ok ? C.ok : C.threat}`, backgroundColor: scen.ok ? "rgba(34,197,94,0.08)" : "rgba(255,77,109,0.10)" }}>
                  <div className="font-mono font-bold text-[19px] tracking-wider" style={{ color: scen.ok ? C.ok : C.threat }}>
                    {scen.ok ? "✓ RESET AUTHORISED" : "✗ RESET BLOCKED"}
                  </div>
                  <div className="mt-1.5 text-[13px]" style={{ color: C.text }}>{scen.reason}</div>
                </motion.div>
              )}
              {phase === "idle" && <div className="mt-5 text-[13px]" style={{ color: C.muted }}>Pick who's calling, then verify before the reset.</div>}
            </AnimatePresence>
          </div>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>The #1 breach vector</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Attackers don't hack MFA — they <b style={{ color: C.text }}>call the helpdesk</b> and talk it into a reset. Knowledge-based checks (employee ID, manager's name) are all stealable.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Voice can't be phished</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>A stranger fails the voiceprint; a <b style={{ color: C.text }}>clone</b> of the real employee is caught by the deepfake check. Neither passes alone.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Defend your own people</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Same ECAPA + deepfake engine as the customer side — turned inward, on the internal helpdesk and privileged-access lines.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
