import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// District / ring detection. Placement note (the question a panel WILL ask): the
// bank does NOT see a scammer calling a villager's personal phone. What it sees is
// the fraud voice CALLING THE BANK — a clone/fraudster ringing the contact centre
// to transact on account after account, impersonating different customers. The
// shield fingerprints every inbound call's voice (campaign correlation,
// app/voiceprints.py); when ONE voice is impersonating many customers, that's a
// ring — all visible because every one of these calls came TO the bank.
//
// Proactive action is what the bank CAN legitimately do: blocklist the voice,
// freeze/review the accounts it already touched, and push a broad fraud advisory
// to its own customers in the affected area over its OWN outbound channel. It does
// NOT (and this demo does not claim to) know who a scammer will call next.
//
// Illustrative scenario (labeled) built on the real voiceprint-correlation feature.

export const Route = createFileRoute("/campaign")({ component: CampaignAlert })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Hit = { cust: string; acct: string; time: string; status: "blocked" | "lost" | "pending" }

// Each row = a call the SAME fraud voice made TO THE BANK, impersonating a
// different customer to move their money. All inbound → all visible to the bank.
const HITS: Hit[] = [
  { cust: "Sunita D.", acct: "…4021", time: "09:12", status: "lost" },
  { cust: "Mohan L.", acct: "…7788", time: "09:41", status: "lost" },
  { cust: "Kamla B.", acct: "…1290", time: "10:03", status: "blocked" },
  { cust: "Ravi K.", acct: "…3345", time: "10:20", status: "blocked" },
  { cust: "Iqbal M.", acct: "…9002", time: "10:47", status: "blocked" },
  { cust: "Geeta R.", acct: "…6714", time: "11:05", status: "pending" },
  { cust: "Phoolwati", acct: "…5567", time: "11:22", status: "pending" },
  { cust: "Bansi P.", acct: "…8830", time: "11:29", status: "pending" },
]

const statusMeta: Record<Hit["status"], { label: string; color: string }> = {
  lost: { label: "money moved (early, pre-pattern)", color: C.threat },
  blocked: { label: "blocked mid-call (voice flagged RED)", color: C.ok },
  pending: { label: "open request — awaiting action", color: C.warn },
}

function CampaignAlert() {
  const [acted, setActed] = useState(false)
  const pending = HITS.filter((h) => h.status === "pending").length
  const lost = HITS.filter((h) => h.status === "lost").length
  const blocked = HITS.filter((h) => h.status === "blocked").length

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · फ़्रॉड रिंग · RING ALERT</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE SCENARIO</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">One voice, impersonating a whole district — caught as a ring</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          The bank can't see the scammer calling villagers — but it <b style={{ color: C.text }}>can</b> see the fraud voice when it
          <b style={{ color: C.text }}> calls the bank</b>. Here one cloned voice rings the contact centre account after account,
          impersonating different customers. Every call is inbound, so the shield fingerprints them all — and the
          <b style={{ color: C.text }}> same voiceprint across many customers</b> is a ring.
        </p>

        {/* ring banner */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: "rgba(255,77,109,0.06)", border: `1px solid ${C.threat}` }}>
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div>
              <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.threat }}>⚠ FRAUD RING DETECTED · voiceprint correlation</div>
              <div className="mt-1 font-mono text-[14px]" style={{ color: C.text }}>cluster <b>#7f3a-c1</b> · one voice · similarity 0.94 across calls</div>
            </div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.threat }}>{HITS.length}</div><div className="text-[11px]" style={{ color: C.muted }}>calls to the bank</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.text }}>{HITS.length}</div><div className="text-[11px]" style={{ color: C.muted }}>customers impersonated</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.warn }}>{pending}</div><div className="text-[11px]" style={{ color: C.muted }}>open requests to hold</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.ok }}>{blocked}</div><div className="text-[11px]" style={{ color: C.muted }}>blocked mid-call</div></div>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          {/* the ring's calls */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>THE RING · same voice, call after call to the bank</div>
            <div className="space-y-1.5">
              {HITS.map((h, i) => {
                const m = statusMeta[h.status]
                const held = acted && h.status === "pending"
                return (
                  <div key={i} className="grid grid-cols-[54px_1fr_auto] items-center gap-3 rounded-lg px-3 py-2" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
                    <span className="font-mono text-[11px]" style={{ color: C.muted }}>{h.time}</span>
                    <span className="text-[13px]" style={{ color: C.text }}>impersonated {h.cust} <span style={{ color: C.muted }}>· acct {h.acct}</span></span>
                    <span className="font-mono text-[10px] text-right" style={{ color: held ? C.cyan : m.color }}>
                      {held ? "✓ held for review" : m.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* the action */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 CONTAIN THE RING</div>
            {!acted ? (
              <>
                <p className="text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
                  The first {lost} moved money before the pattern was clear. Now the voice is a known ring — the bank acts on what it controls:
                </p>
                <ul className="mt-3 space-y-2 text-[13px]" style={{ color: C.text }}>
                  <li>• <b>Blocklist</b> voiceprint <b>#7f3a-c1</b> — every future call with it auto-flags RED</li>
                  <li>• <b>Freeze &amp; review</b> the {pending} open requests + the {lost} already actioned</li>
                  <li>• Push a <b>fraud advisory</b> to Rampur-block customers on the bank's own SMS / IVR</li>
                </ul>
                <button onClick={() => setActed(true)}
                  className="mt-5 w-full rounded-xl py-3 font-mono text-[13px] font-bold tracking-wider" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                  ▶ CONTAIN THE RING
                </button>
              </>
            ) : (
              <AnimatePresence>
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <div className="rounded-xl px-4 py-4" style={{ border: `1px solid ${C.ok}`, backgroundColor: "rgba(34,197,94,0.08)" }}>
                    <div className="font-mono font-bold text-[16px]" style={{ color: C.ok }}>✓ RING CONTAINED</div>
                    <ul className="mt-2 space-y-1.5 text-[13px]" style={{ color: C.text }}>
                      <li>✓ Voice <b>#7f3a-c1</b> blocklisted — future calls auto-flag</li>
                      <li>✓ <b>{pending}</b> open requests held for manual review</li>
                      <li>✓ Fraud advisory queued to Rampur-block customers (bank SMS / IVR)</li>
                    </ul>
                  </div>
                  <p className="mt-3 text-[12px]" style={{ color: C.muted, lineHeight: 1.6 }}>
                    Stopped by the <b style={{ color: C.text }}>pattern across calls to the bank</b> — not by any one villager reporting it.
                  </p>
                </motion.div>
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* explanation */}
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>What the bank actually sees</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Only calls that reach the bank. It can't watch a scammer dial a villager — but a clone ringing the contact centre to loot account after account is fully visible, and its voiceprint ties the calls together.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Why it matters rurally</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The individual villager is silent — but the <b style={{ color: C.text }}>ring isn't</b>. One blocklist + one freeze + one advisory protects the whole block from a fraud the customers never reported.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>What it does NOT claim</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>It does not know who a scammer will call next. The advisory is a <b style={{ color: C.text }}>broad</b> alert to the bank's own customers in the area — honest about the limit.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
