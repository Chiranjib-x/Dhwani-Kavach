import { createFileRoute } from "@tanstack/react-router"
import { motion } from "framer-motion"

// Hub for the bank's OWN security features — the "voice-trust layer" thesis:
// the same engine that protects customers can defend the bank's money, its
// people, its front door, and its vulnerable customers. Everything here runs
// bank-side, on a voice channel the bank already operates.

export const Route = createFileRoute("/voice-trust")({ component: VoiceTrustHub })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Feat = { tag: string; color: string; title: string; desc: string; href: string; guards: string }

const FEATS: Feat[] = [
  { tag: "THE BANK'S MONEY", color: "#FF4D6D", title: "Treasury callback", href: "/treasury", guards: "protects the vault",
    desc: "A cloned executive can't authorise a high-value wire — voiceprint + synthetic-voice check on the treasury callback. Stops deepfake-CEO fraud (the Arup US$25M case)." },
  { tag: "THE BANK'S PEOPLE", color: "#F59E0B", title: "Helpdesk firewall", href: "/helpdesk", guards: "shuts the #1 breach vector",
    desc: "The 'employee' calling IT to reset MFA must pass their voiceprint + liveness. Closes helpdesk social-engineering — how banks actually get breached." },
  { tag: "THE FRONT DOOR", color: "#38BDF8", title: "Onboarding screen", href: "/onboarding", guards: "blocks synthetic identities",
    desc: "Block deepfake video-KYC, enrol a lifelong voiceprint, and catch mule rings by voiceprint reuse — one voice behind many 'different' accounts." },
  { tag: "THE WHOLE CALL", color: "#5EEAD4", title: "Continuous auth", href: "/continuous", guards: "catches the hand-off",
    desc: "Run the voiceprint the whole call, not just at the gate — and flag the moment the customer hands the phone to a coached third party. A primitive that doesn't exist today." },
  { tag: "THE CUSTOMER'S WELFARE", color: "#A78BFA", title: "Safeguarding", href: "/safeguarding", guards: "a guardian, not a gate",
    desc: "Hear elder abuse, coercion or distress on the call and route to a safeguarding team for a welfare check — not a cold block. A rising regulatory duty." },
]

function VoiceTrustHub() {
  return (
    <div className="min-h-screen px-6 py-12" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-6xl mx-auto">
        <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · VOICE-TRUST LAYER</div>
        <h1 className="mt-3 text-3xl md:text-4xl font-bold" style={{ letterSpacing: "-0.02em", maxWidth: 820, lineHeight: 1.1 }}>
          Not a contact-centre tool — a voice-trust layer for the whole bank
        </h1>
        <p className="mt-4 text-[15px] max-w-3xl" style={{ color: "#CBD5E1", lineHeight: 1.6 }}>
          The same engine that verifies a customer can defend the bank <b style={{ color: C.text }}>itself</b>: its money, its people, its front door,
          and its most vulnerable customers. A bank runs dozens of voice channels — and the biggest, least-defended threats now live on the
          <b style={{ color: C.text }}> internal</b> ones. Deploy once, defend all of them. <span style={{ color: C.muted }}>Everything here runs bank-side, on a voice the bank already handles.</span>
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {FEATS.map((f, i) => (
            <motion.a key={f.href} href={f.href}
              initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.45, delay: i * 0.06 }}
              className="group flex flex-col rounded-2xl p-6 transition-colors"
              style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = f.color)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.faint)}>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: f.color }} />
                <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: f.color }}>{f.tag}</span>
              </div>
              <div className="mt-4 text-[18px] font-semibold" style={{ color: C.text }}>{f.title}</div>
              <div className="mt-2 text-[13px] flex-1" style={{ color: C.muted, lineHeight: 1.55 }}>{f.desc}</div>
              <div className="mt-5 flex items-center justify-between">
                <span className="font-mono text-[11px]" style={{ color: C.muted }}>{f.guards}</span>
                <span className="font-mono text-[12px] transition-colors" style={{ color: f.color }}>open →</span>
              </div>
            </motion.a>
          ))}
          {/* thesis card */}
          <div className="flex flex-col justify-center rounded-2xl p-6" style={{ border: `1px dashed ${C.faint}` }}>
            <div className="text-[15px] font-semibold" style={{ color: C.cyan }}>One engine, turned in every direction</div>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
              Voiceprints, liveness and intent aren't a feature — they're a trust fabric. The same ECAPA + deepfake + APP-fraud stack, pointed
              at each voice channel the bank runs.
            </p>
          </div>
        </div>

        <div className="mt-10 rounded-2xl px-6 py-5" style={{ border: `1px solid ${C.faint}`, backgroundColor: C.surface }}>
          <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.cyan }}>THE PITCH LINE</span>
          <p className="mt-2 text-[16px]" style={{ color: C.text, lineHeight: 1.5 }}>
            "Voiceprints, liveness and intent are a trust layer for <b>every</b> voice your bank runs — your customers, your executives'
            authorisations, and your own employees. Deploy it once, defend all three."
          </p>
        </div>

        <div className="mt-8 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
