import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// Attack Range — the integration demo for a bank panel. A mock bank runs a
// transfer; an attacker launches a THREAT.md vector at it; a master toggle turns
// the shield on/off. The whole pitch is the A/B: with the shield OFF the fraud
// completes and the money leaves; flip it ON and the same attack is caught and
// escalated. Attacks feed pre-verified clips DIGITALLY into /api/analyze (never
// speaker->air->mic), so verdicts are deterministic on stage.

export const Route = createFileRoute("/range")({ component: AttackRange })

const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000"

type Action = "MONITOR" | "CHALLENGE" | "BLOCK"
type Analysis = {
  risk_score: number; alert_level: string; action?: Action; action_reason?: string
  scam?: { score: number; tactics: string[] }
  replay?: { suspect: boolean; score: number }
  escalation?: { required: boolean; method: "voice_otp" | "human_review" | null; reason: string }
}
type Attack = {
  id: string; label: string; tag: string; tagColor: string; file: string
  amount: number; newBeneficiary: boolean; blurb: string; caughtBy: string
}

const ATTACKS: Attack[] = [
  { id: "clone", label: "AI voice clone", tag: "DEEPFAKE", tagColor: "#FF4D6D", file: "clone.mp3",
    amount: 500000, newBeneficiary: true, caughtBy: "Dual neural core",
    blurb: "A cloned customer voice calls in and authorises a large transfer to a brand-new payee." },
  { id: "replay", label: "Loudspeaker replay", tag: "CHANNEL", tagColor: "#F59E0B", file: "replay.mp3",
    amount: 500000, newBeneficiary: true, caughtBy: "Neural + replay-channel gate",
    blurb: "A pre-made clone played through a speaker into the live call — the artifacts smear, the channel doesn't lie." },
  { id: "normal", label: "Genuine customer", tag: "CONTROL", tagColor: "#22C55E", file: "normal.mp3",
    amount: 8000, newBeneficiary: false, caughtBy: "—",
    blurb: "A real customer making a routine payment to a known payee. Proves the shield doesn't cry wolf." },
]

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }
const inr = (n: number) => "₹" + n.toLocaleString("en-IN")
const actionColor = (a?: Action) => (a === "BLOCK" ? C.threat : a === "CHALLENGE" ? C.warn : C.ok)

function AttackRange() {
  const [shieldOn, setShieldOn] = useState(true)
  const [attack, setAttack] = useState<Attack>(ATTACKS[0])
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle")
  const [result, setResult] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)

  const launch = useCallback(async () => {
    setError(null); setResult(null); setPhase("running")
    try {
      const blob = await (await fetch(`/attacks/${attack.file}`)).blob()
      const form = new FormData()
      form.append("audio", blob, attack.file)
      form.append("amount", String(attack.amount))
      form.append("new_beneficiary", String(attack.newBeneficiary))
      const resp = await fetch(`${BACKEND}/api/analyze`, { method: "POST", body: form })
      if (!resp.ok) throw new Error(`Server ${resp.status} — is the backend on :8000?`)
      // brief theatrical beat so the verdict doesn't just pop
      await new Promise((r) => setTimeout(r, 700))
      setResult(await resp.json())
      setPhase("done")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setPhase("idle")
    }
  }, [attack])

  // Bank decision. Shield OFF: the verdict is never consulted -> the transfer
  // always completes (fraud succeeds). Shield ON: the bank acts on the verdict.
  const consulted = shieldOn && phase === "done" && result
  const stopped = Boolean(consulted && result!.action !== "MONITOR")
  const completed = phase === "done" && !stopped
  const isFraud = attack.id !== "normal"

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-6xl mx-auto">
        {/* header + master toggle */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · ATTACK RANGE</div>
            <h1 className="mt-2 text-2xl font-semibold">Mock bank vs. live attacker</h1>
            <p className="mt-1 text-[13px]" style={{ color: C.muted }}>Launch an attack, then flip the shield. The money is the message.</p>
          </div>
          <button onClick={() => { setShieldOn((s) => !s); setPhase("idle"); setResult(null) }}
            className="rounded-xl px-5 py-3 text-left transition-colors"
            style={{ border: `1px solid ${shieldOn ? C.ok : C.threat}`, backgroundColor: shieldOn ? "rgba(34,197,94,0.08)" : "rgba(255,77,109,0.08)" }}>
            <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>DHWANI-KAVACH SHIELD</div>
            <div className="mt-1 font-mono font-bold text-[18px] tracking-wider" style={{ color: shieldOn ? C.ok : C.threat }}>
              {shieldOn ? "● ON — enforcing" : "○ OFF — disabled"}
            </div>
            <div className="mt-0.5 text-[11px]" style={{ color: C.muted }}>click to toggle</div>
          </button>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {/* ATTACKER */}
          <div className="rounded-2xl p-6" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-4" style={{ color: C.threat }}>◢ ATTACKER CONSOLE</div>
            <div className="space-y-2">
              {ATTACKS.map((a) => (
                <button key={a.id} onClick={() => { setAttack(a); setPhase("idle"); setResult(null) }}
                  className="w-full text-left rounded-xl px-4 py-3 transition-colors"
                  style={{ border: `1px solid ${attack.id === a.id ? a.tagColor : C.faint}`, backgroundColor: attack.id === a.id ? "rgba(255,255,255,0.03)" : "transparent" }}>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] tracking-[0.15em] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${a.tagColor}`, color: a.tagColor }}>{a.tag}</span>
                    <span className="text-[14px] font-medium">{a.label}</span>
                  </div>
                  <div className="mt-1.5 text-[12px]" style={{ color: C.muted, lineHeight: 1.5 }}>{a.blurb}</div>
                </button>
              ))}
            </div>
            <button onClick={launch} disabled={phase === "running"}
              className="mt-5 w-full rounded-xl py-3 font-mono text-[13px] font-bold tracking-wider transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${attack.tagColor}`, color: attack.tagColor }}>
              {phase === "running" ? "LAUNCHING…" : `▶ LAUNCH — ${attack.label.toUpperCase()}`}
            </button>
            {error && <div className="mt-3 font-mono text-[11px]" style={{ color: C.threat }}>{error}</div>}
          </div>

          {/* BANK */}
          <div className="rounded-2xl p-6" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-4" style={{ color: C.cyan }}>▣ BANK — AGENT SCREEN</div>

            {/* the transaction on the table */}
            <div className="rounded-xl px-4 py-3" style={{ border: `1px solid ${C.faint}` }}>
              <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>REQUESTED TRANSFER</div>
              <div className="mt-1 font-mono text-[26px] font-bold" style={{ color: C.text }}>{inr(attack.amount)}</div>
              <div className="mt-0.5 text-[12px]" style={{ color: attack.newBeneficiary ? C.warn : C.muted }}>
                {attack.newBeneficiary ? "→ NEW beneficiary (never paid before)" : "→ known payee"}
              </div>
            </div>

            {/* shield verdict */}
            <div className="mt-4 rounded-xl px-4 py-3" style={{ border: `1px solid ${shieldOn ? actionColor(result?.action) : C.muted}`, opacity: shieldOn ? 1 : 0.55 }}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>SHIELD VERDICT</span>
                {!shieldOn && <span className="font-mono text-[10px]" style={{ color: C.threat }}>NOT CONSULTED — shield off</span>}
              </div>
              {phase === "running" && <div className="mt-2 font-mono text-[13px] animate-pulse" style={{ color: C.cyan }}>analyzing call…</div>}
              {phase === "done" && result && (
                <div className="mt-2">
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono font-bold text-[22px]" style={{ color: actionColor(result.action) }}>{result.action}</span>
                    <span className="font-mono text-[13px]" style={{ color: C.muted }}>risk {result.risk_score}/100 · {result.alert_level}</span>
                  </div>
                  {result.action_reason && <div className="mt-1 text-[12px]" style={{ color: C.muted }}>{result.action_reason}</div>}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.replay?.suspect && <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.threat}`, color: C.threat }}>replay signature</span>}
                    {(result.scam?.score ?? 0) >= 70 && <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.warn}`, color: C.warn }}>APP-fraud {result.scam!.score}</span>}
                    {result.escalation?.required && (
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.info}`, color: C.info }}>
                        ↳ {result.escalation.method === "human_review" ? "route to human" : "step-up voice-OTP"}
                      </span>
                    )}
                  </div>
                </div>
              )}
              {phase === "idle" && <div className="mt-2 text-[12px]" style={{ color: C.muted }}>awaiting the call…</div>}
            </div>

            {/* OUTCOME — the money */}
            <AnimatePresence mode="wait">
              {phase === "done" && (
                <motion.div key={stopped ? "stop" : "go"} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="mt-4 rounded-xl px-5 py-4 text-center"
                  style={{ border: `1px solid ${stopped ? C.ok : (isFraud ? C.threat : C.ok)}`, backgroundColor: stopped ? "rgba(34,197,94,0.08)" : (isFraud ? "rgba(255,77,109,0.10)" : "rgba(34,197,94,0.06)") }}>
                  <div className="font-mono font-bold text-[20px] tracking-wider" style={{ color: stopped ? C.ok : (isFraud ? C.threat : C.ok) }}>
                    {stopped ? "✓ TRANSFER STOPPED" : (isFraud ? "✗ TRANSFER COMPLETED" : "✓ TRANSFER COMPLETED")}
                  </div>
                  <div className="mt-1 text-[13px]" style={{ color: C.text }}>
                    {stopped
                      ? `${inr(attack.amount)} held — caught by ${attack.caughtBy}, stepped up before the money moved.`
                      : isFraud
                        ? `${inr(attack.amount)} left the account. Fraud succeeded — the shield was off and never consulted.`
                        : `${inr(attack.amount)} sent to a known payee. No false alarm.`}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* the pitch line */}
        <div className="mt-8 text-center text-[13px]" style={{ color: C.muted }}>
          {completed && isFraud
            ? "This is a bank with no audio-forensics layer. Flip the shield ON and launch the same attack."
            : stopped
              ? "Same attack, shield ON — caught in seconds, on the agent's screen, before the money moved."
              : "Pick an attack, toggle the shield, and watch the money."}
        </div>
        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
