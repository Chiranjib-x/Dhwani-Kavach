import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Bank Mitra (Business Correspondent) verification. In a village with no branch,
// the BC *is* the bank — and an impersonated or cloned Mitra is a direct fraud
// node the customer has no way to check. So we voiceprint every Mitra (ECAPA, the
// same engine as /voiceprint) and verify their voice on each visit. Two checks,
// because a clone is the hard case: a 1:1 voiceprint alone can be partly fooled by
// a good clone, so the deepfake detector runs alongside it.
//
// Illustrative scenario (labeled) with realistic numbers from the real ECAPA
// engine (same-voice ~0.8, other ~0.15, clone ~0.7 — passes voiceprint alone,
// caught by the synthetic-voice check). Live 1:1 verification is at /voiceprint.

export const Route = createFileRoute("/mitra")({ component: MitraVerify })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }
const ACCEPT = 0.40   // config.ASV_ACCEPT — speaker-match threshold

type Scenario = {
  id: string; label: string; sub: string; cosine: number; deepfakeRed: boolean
  verdict: "VERIFIED" | "REJECTED"; reason: string; note: string; color: string
}

const SCENARIOS: Scenario[] = [
  {
    id: "genuine", label: "The real Bank Mitra", sub: "Ramesh, the enrolled agent, arrives",
    cosine: 0.82, deepfakeRed: false, verdict: "VERIFIED", color: "#22C55E",
    reason: "Voice matches the enrolled Mitra, and it's a live human.",
    note: "The customer can trust this is really their Bank Mitra — confirmed by voice, not by an ID card they can't read.",
  },
  {
    id: "impostor", label: "A different person", sub: "someone else claims to be the Mitra",
    cosine: 0.14, deepfakeRed: false, verdict: "REJECTED", color: "#FF4D6D",
    reason: "Voice does not match the enrolled Mitra — VOICE_MISMATCH.",
    note: "A stranger posing as the Bank Mitra is caught instantly: their voiceprint simply isn't the enrolled one.",
  },
  {
    id: "clone", label: "An AI clone of the Mitra", sub: "a synthetic copy of Ramesh's voice",
    cosine: 0.71, deepfakeRed: true, verdict: "REJECTED", color: "#F59E0B",
    reason: "Voiceprint alone would PASS (0.71 ≥ 0.40) — but the synthetic-voice check flags it.",
    note: "This is why two checks matter: a good clone can partly fool a 1:1 voiceprint, so the deepfake detector runs alongside it and catches the synthesis.",
  },
]

function MitraVerify() {
  const [scenario, setScenario] = useState<Scenario>(SCENARIOS[0])
  const [phase, setPhase] = useState<"idle" | "checking" | "done">("idle")
  const [cos, setCos] = useState(0)

  const verify = useCallback(() => {
    setPhase("checking"); setCos(0)
    const t = setTimeout(() => { setCos(scenario.cosine); setPhase("done") }, 1100)
    return () => clearTimeout(t)
  }, [scenario])

  const pick = (s: Scenario) => { setScenario(s); setPhase("idle"); setCos(0) }
  const cosColor = cos >= ACCEPT ? (scenario.deepfakeRed ? C.warn : C.ok) : C.threat

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · बैंक मित्र</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE SCENARIO</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">Is this really your Bank Mitra?</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          In a village with no branch, the <b style={{ color: C.text }}>Business Correspondent (Bank Mitra)</b> is the bank — and a
          customer has no way to tell a genuine Mitra from an impostor or a cloned voice. So we <b style={{ color: C.text }}>voiceprint
          every Mitra once</b> and verify their voice on each visit. A stranger fails the voiceprint; an AI clone that partly
          matches is caught by the synthetic-voice check.
        </p>

        {/* enrolled agent */}
        <div className="mt-6 rounded-2xl p-4 flex items-center gap-4" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="w-11 h-11 rounded-full flex items-center justify-center font-mono text-[15px]" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>रा</div>
          <div>
            <div className="text-[14px] font-medium">Enrolled Bank Mitra · Ramesh Kumar</div>
            <div className="font-mono text-[11px]" style={{ color: C.muted }}>voiceprint stored (ECAPA embedding) · device ID · service area: Rampur block</div>
          </div>
          <span className="ml-auto font-mono text-[10px] px-2 py-1 rounded-full" style={{ border: `1px solid ${C.ok}`, color: C.ok }}>✓ ENROLLED</span>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* who's at the door */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>WHO'S CLAIMING TO BE THE MITRA?</div>
            <div className="space-y-2">
              {SCENARIOS.map((s) => (
                <button key={s.id} onClick={() => pick(s)} disabled={phase === "checking"}
                  className="w-full text-left rounded-xl px-4 py-3 transition-colors disabled:opacity-50"
                  style={{ border: `1px solid ${scenario.id === s.id ? s.color : C.faint}`, backgroundColor: scenario.id === s.id ? "rgba(255,255,255,0.03)" : "transparent" }}>
                  <div className="text-[14px] font-medium">{s.label}</div>
                  <div className="text-[12px]" style={{ color: C.muted }}>{s.sub}</div>
                </button>
              ))}
            </div>
            <button onClick={verify} disabled={phase === "checking"}
              className="mt-4 w-full rounded-xl py-3 font-mono text-[13px] font-bold tracking-wider transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
              {phase === "checking" ? "VERIFYING VOICE…" : "▶ VERIFY THE MITRA'S VOICE"}
            </button>
          </div>

          {/* result */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 VERIFICATION</div>

            <div>
              <div className="flex items-end justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>VOICEPRINT MATCH (cosine)</span>
                <span className="font-mono font-bold text-[28px] leading-none" style={{ color: phase === "done" ? cosColor : C.muted }}>
                  {phase === "done" ? cos.toFixed(2) : "—"}
                </span>
              </div>
              <div className="relative mt-2 h-[8px] w-full rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                <motion.div animate={{ width: `${cos * 100}%` }} transition={{ duration: 0.8 }} style={{ height: "100%", backgroundColor: cosColor }} />
                {/* accept threshold marker */}
                <div className="absolute top-0 h-full" style={{ left: `${ACCEPT * 100}%`, width: 2, backgroundColor: C.text, opacity: 0.5 }} />
              </div>
              <div className="font-mono text-[10px] mt-1" style={{ color: C.muted }}>accept ≥ {ACCEPT.toFixed(2)} (marker)</div>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>SYNTHETIC-VOICE CHECK</span>
              {phase === "done"
                ? <span className="font-mono text-[11px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${scenario.deepfakeRed ? C.threat : C.ok}`, color: scenario.deepfakeRed ? C.threat : C.ok }}>{scenario.deepfakeRed ? "RED · clone detected" : "GREEN · live human"}</span>
                : <span className="font-mono text-[11px]" style={{ color: C.muted }}>—</span>}
            </div>

            <AnimatePresence mode="wait">
              {phase === "done" && (
                <motion.div key={scenario.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="mt-5 rounded-xl px-4 py-4" style={{ border: `1px solid ${scenario.color}`, backgroundColor: `${scenario.color}14` }}>
                  <div className="font-mono font-bold text-[20px] tracking-wider" style={{ color: scenario.color }}>
                    {scenario.verdict === "VERIFIED" ? "✓ MITRA VERIFIED" : "✗ REJECTED · impersonation"}
                  </div>
                  <div className="mt-1.5 text-[13px]" style={{ color: C.text }}>{scenario.reason}</div>
                </motion.div>
              )}
              {phase === "idle" && <div className="mt-5 text-[13px]" style={{ color: C.muted }}>Pick who's at the door, then verify their voice.</div>}
            </AnimatePresence>
          </div>
        </div>

        {/* takeaway */}
        <AnimatePresence>
          {phase === "done" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="mt-6 rounded-xl px-5 py-4" style={{ border: `1px solid ${C.faint}`, backgroundColor: C.surface }}>
              <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.cyan }}>WHY IT MATTERS</span>
              <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>{scenario.note}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* explanation */}
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>The BC is a fraud node</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Where the Bank Mitra <i>is</i> the bank, impersonation or a bribed/cloned agent is a direct attack the villager can't detect. Voiceprinting the Mitra closes it.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Same real engine</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The 1:1 voiceprint is real ECAPA — try it live at <a href="/voiceprint" className="underline" style={{ color: C.cyan }}>/voiceprint</a> (enrol once, verify by voice). Here it's applied to the <b style={{ color: C.text }}>agent</b>, not the customer.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Two checks, one reason</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>A stranger fails the voiceprint outright; a <b style={{ color: C.text }}>clone</b> that partly matches is caught by the synthetic-voice detector. Neither passes alone.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
