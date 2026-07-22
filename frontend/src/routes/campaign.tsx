import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

// District campaign alerting. Rural victims rarely report — so protection can't
// wait for complaints. The shield already fingerprints every call's voice
// (campaign correlation, app/voiceprints.py). Point it at a district: when ONE
// fraud voice sweeps many villages, blocklist it and PROACTIVELY warn everyone
// else it's calling — community-level protection where the individual is silent.
//
// Illustrative scenario (labeled) built on the real campaign-correlation feature.

export const Route = createFileRoute("/campaign")({ component: CampaignAlert })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Hit = { village: string; who: string; time: string; status: "blocked" | "lost" | "atrisk" }

const HITS: Hit[] = [
  { village: "Rampur", who: "Sunita D.", time: "09:12", status: "lost" },
  { village: "Rampur", who: "Mohan L.", time: "09:41", status: "lost" },
  { village: "Bhoja", who: "Kamla B.", time: "10:03", status: "blocked" },
  { village: "Bhoja", who: "Ravi K.", time: "10:20", status: "blocked" },
  { village: "Salaiya", who: "Iqbal M.", time: "10:47", status: "blocked" },
  { village: "Salaiya", who: "Geeta R.", time: "11:05", status: "atrisk" },
  { village: "Tenda", who: "Phoolwati", time: "11:22", status: "atrisk" },
  { village: "Tenda", who: "Bansi P.", time: "11:29", status: "atrisk" },
]

const statusMeta: Record<Hit["status"], { label: string; color: string }> = {
  lost: { label: "money lost (early, pre-detection)", color: C.threat },
  blocked: { label: "blocked (voice on blocklist)", color: C.ok },
  atrisk: { label: "still being called — not yet warned", color: C.warn },
}

function CampaignAlert() {
  const [protectedDistrict, setProtectedDistrict] = useState(false)
  const villages = [...new Set(HITS.map((h) => h.village))]
  const atRisk = HITS.filter((h) => h.status === "atrisk").length
  const lost = HITS.filter((h) => h.status === "lost").length
  const blocked = HITS.filter((h) => h.status === "blocked").length

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-wrap items-baseline gap-3">
          <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · ज़िला अलर्ट · DISTRICT ALERT</div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded-full" style={{ border: `1px solid ${C.muted}`, color: C.muted }}>ILLUSTRATIVE SCENARIO</span>
        </div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">One fraud voice, a whole district — caught as a ring</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          Rural victims rarely report a scam — so protection can't wait for complaints. The shield <b style={{ color: C.text }}>fingerprints every
          call's voice</b>. When the same synthetic voice sweeps village after village, we see the <b style={{ color: C.text }}>ring</b> — and can
          protect the people it hasn't reached yet.
        </p>

        {/* campaign banner */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: "rgba(255,77,109,0.06)", border: `1px solid ${C.threat}` }}>
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div>
              <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.threat }}>⚠ FRAUD CAMPAIGN DETECTED</div>
              <div className="mt-1 font-mono text-[14px]" style={{ color: C.text }}>voiceprint cluster <b>#7f3a-c1</b> · similarity 0.94</div>
            </div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.threat }}>{HITS.length}</div><div className="text-[11px]" style={{ color: C.muted }}>customers called</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.text }}>{villages.length}</div><div className="text-[11px]" style={{ color: C.muted }}>villages · Rampur block</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.warn }}>{atRisk}</div><div className="text-[11px]" style={{ color: C.muted }}>still at risk</div></div>
            <div><div className="font-mono font-bold text-[26px]" style={{ color: C.ok }}>{blocked}</div><div className="text-[11px]" style={{ color: C.muted }}>already blocked</div></div>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          {/* the sweep */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>THE SWEEP · same voice, village by village</div>
            <div className="space-y-1.5">
              {HITS.map((h, i) => {
                const m = statusMeta[h.status]
                const warned = protectedDistrict && h.status === "atrisk"
                return (
                  <div key={i} className="grid grid-cols-[54px_1fr_auto] items-center gap-3 rounded-lg px-3 py-2" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
                    <span className="font-mono text-[11px]" style={{ color: C.muted }}>{h.time}</span>
                    <span className="text-[13px]" style={{ color: C.text }}>{h.who} <span style={{ color: C.muted }}>· {h.village}</span></span>
                    <span className="font-mono text-[10px] text-right" style={{ color: warned ? C.cyan : m.color }}>
                      {warned ? "✓ warned proactively" : m.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* the action */}
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.cyan }}>🛡 PROTECT THE DISTRICT</div>
            {!protectedDistrict ? (
              <>
                <p className="text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
                  The first {lost} lost money before the pattern was clear. Now the voice is a known ring — one action protects everyone else:
                </p>
                <ul className="mt-3 space-y-2 text-[13px]" style={{ color: C.text }}>
                  <li>• Blocklist voiceprint <b>#7f3a-c1</b> across the district</li>
                  <li>• Speak a vernacular warning to the <b>{atRisk} still-at-risk</b> customers</li>
                  <li>• Alert the Bank Mitras in Rampur block</li>
                </ul>
                <button onClick={() => setProtectedDistrict(true)}
                  className="mt-5 w-full rounded-xl py-3 font-mono text-[13px] font-bold tracking-wider" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                  ▶ PROTECT RAMPUR BLOCK
                </button>
              </>
            ) : (
              <AnimatePresence>
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <div className="rounded-xl px-4 py-4" style={{ border: `1px solid ${C.ok}`, backgroundColor: "rgba(34,197,94,0.08)" }}>
                    <div className="font-mono font-bold text-[16px]" style={{ color: C.ok }}>✓ DISTRICT PROTECTED</div>
                    <ul className="mt-2 space-y-1.5 text-[13px]" style={{ color: C.text }}>
                      <li>✓ Voice <b>#7f3a-c1</b> blocklisted — every future call auto-flags</li>
                      <li>✓ <b>{atRisk}</b> at-risk customers sent a spoken Hindi warning</li>
                      <li>✓ Bank Mitras in {villages.length} villages alerted</li>
                    </ul>
                  </div>
                  <p className="mt-3 text-[12px]" style={{ color: C.muted, lineHeight: 1.6 }}>
                    None of the {atRisk} had reported anything. The ring was stopped by the <b style={{ color: C.text }}>pattern</b>, not a complaint.
                  </p>
                </motion.div>
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* explanation */}
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Where the signal comes from</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Every scored call gets a voiceprint (same forward pass, free). Cosine-matching links the same voice across calls — the real campaign feature, already at <span className="font-mono">/campaigns</span>.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Why it matters rurally</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>The individual villager is silent — but the <b style={{ color: C.text }}>district isn't</b>. One ring, one blocklist, one warning wave protects everyone the fraud hasn't reached.</p>
          </div>
          <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
            <h3 className="text-[14px] font-semibold" style={{ color: C.cyan }}>Proactive, not post-mortem</h3>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>Instead of investigating losses after the fact, the bank <b style={{ color: C.text }}>gets ahead of the ring</b> mid-sweep — the difference between {lost} losses and {atRisk} more.</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
