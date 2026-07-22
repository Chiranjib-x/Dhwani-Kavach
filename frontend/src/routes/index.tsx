import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import Nav from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import LiveDemo from "@/components/LiveDemo";
import LiveMonitor from "@/components/LiveMonitor";
import RiskGauge from "@/components/RiskGauge";

const HeroShield = lazy(() => import("@/components/HeroShield"));

const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dhwani Kavach — Real-time AI Voice Deepfake Detection" },
      { name: "description", content: "Detect AI-cloned voices on live banking calls in seconds — a self-supervised neural detector, cross-checked by acoustic signals, that says UNCERTAIN when the line is too poor to judge." },
    ],
  }),
  component: Index,
});

const LAYERS = [
  { n: "01", name: "Dual Neural Core", desc: "Two independent XLS-R detectors, trained on different clone families, cross-check every window — their blind spots don't overlap" },
  { n: "02", name: "Acoustic Corroboration", desc: "MFCC, breath rhythm, phase coherence and liveness back the verdict — evidence the neural core can point to" },
  { n: "03", name: "APP-Fraud & Coercion", desc: "Reads the conversation, not just the voice — a real customer being coached or coerced in real time, invisible to any deepfake detector" },
  { n: "04", name: "Replay-Channel Gate", desc: "A clone played through a loudspeaker smears its own artifacts — so we catch the channel instead, and never trust a speaker playback" },
  { n: "05", name: "Input-Quality Abstention", desc: "Too quiet, clipped or noisy to judge? It says UNCERTAIN instead of a false all-clear" },
  { n: "06", name: "Decision → Step-Up", desc: "Fuses everything into MONITOR / CHALLENGE / BLOCK, then escalates a flagged call into voice-OTP, a 1:1 voiceprint, or a human" },
];

const THREATS = [
  { n: "01", t: "Capture", d: "3 seconds of audio is enough to clone a voice" },
  { n: "02", t: "Synthesize", d: "ElevenLabs-style cloning forges a trusted voiceprint" },
  { n: "03", t: "Exploit", d: "The deepfake authorizes a transfer. Ears can't tell." },
];

// Illustrative per-signal readout for ONE flagged call (not accuracy stats):
// the neural detector drives the verdict; the acoustic signals are corroborating
// evidence, so they read lower and don't dominate.
const DASHBOARD_LAYERS = [
  { name: "Neural core", v: 96 },
  { name: "Acoustic evidence", v: 43 },
  { name: "APP-fraud / coercion", v: 24 },
  { name: "Replay channel", v: 9 },
  { name: "Active liveness", v: 88 },
];

function Index() {
  return (
    <div id="top" className="min-h-screen" style={{ backgroundColor: "#08090C" }}>
      <Nav />

      {/* HERO */}
      <section className="relative min-h-screen w-full flex items-center justify-center overflow-hidden px-6">
        <div className="absolute inset-0 z-0" style={{ pointerEvents: "none" }}>
          <Suspense fallback={null}>
            <HeroShield />
          </Suspense>
        </div>
        <div className="absolute inset-0 z-[1]" style={{
          background: "radial-gradient(ellipse at center, rgba(8,9,12,0.4) 0%, #08090C 75%)",
          pointerEvents: "none",
        }} />
        <div className="relative z-10 max-w-[760px] text-center">
          <p className="font-mono" style={{ color: "#5EEAD4", fontSize: "0.7rem", letterSpacing: "0.12em" }}>
            REAL-TIME VOICE AUTHENTICATION
          </p>
          <h1
            className="mt-6 font-bold mx-auto"
            style={{
              color: "#F1F5F9",
              fontSize: "clamp(2.5rem, 5vw, 4.5rem)",
              maxWidth: 700,
              lineHeight: 1.15,
              letterSpacing: "-0.02em",
            }}
          >
            Your customer's voice. Verified in real time.
          </h1>
          <p className="mt-6 mx-auto" style={{ color: "#64748B", fontSize: "1.1rem", maxWidth: 560, lineHeight: 1.5 }}>
            Dhwani Kavach flags AI-cloned voices <span style={{ color: "#94A3B8" }}>and coached, coerced customers</span> on
            live banking calls — then steps the call up to a voice-OTP or a human, before the money moves.
          </p>
          <div className="mt-10">
            <a
              href="#threat"
              className="inline-flex items-center gap-2 rounded-full px-5 py-2 text-[13px] font-medium transition-colors duration-200 group"
              style={{ border: "1px solid #5EEAD4", color: "#5EEAD4", backgroundColor: "transparent" }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "#5EEAD4"; e.currentTarget.style.color = "#08090C"; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "transparent"; e.currentTarget.style.color = "#5EEAD4"; }}
            >
              See how it works →
            </a>
          </div>
        </div>
      </section>

      {/* THREAT */}
      <section id="threat" className="px-6 py-32 md:py-40">
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em", maxWidth: 720 }}>
              A cloned voice can fool a human. It can't fool physics.
            </h2>
          </Reveal>

          <div className="mt-16 border-t" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
            {THREATS.map((row, i) => (
              <motion.div
                key={row.n}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ duration: 0.5, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] }}
                className="grid grid-cols-[auto_1fr] md:grid-cols-[80px_220px_1fr] gap-x-6 md:gap-x-10 gap-y-2 py-8 border-b"
                style={{ borderColor: "rgba(255,255,255,0.07)" }}
              >
                <div className="font-mono text-[13px]" style={{ color: "#5EEAD4" }}>{row.n}</div>
                <div className="text-[18px] md:text-[20px] font-semibold col-span-1" style={{ color: "#F1F5F9" }}>{row.t}</div>
                <div className="col-span-2 md:col-span-1 text-[15px]" style={{ color: "#64748B", lineHeight: 1.55 }}>{row.d}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FIVE LAYERS */}
      <section id="defense" className="px-6 py-32 md:py-40">
        <div className="max-w-[680px] mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              A neural core. Cross-checked.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center" style={{ color: "#64748B", fontSize: "1rem" }}>
              A self-supervised neural detector makes the call; acoustic signals corroborate it. When the
              line is too degraded to be sure, it says UNCERTAIN instead of guessing.
            </p>
          </Reveal>

          <div className="mt-16 space-y-1">
            {LAYERS.map((l, i) => (
              <motion.div
                key={l.n}
                initial={{ opacity: 0, x: -8 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.6 }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="relative pl-6 py-5 grid grid-cols-[56px_1fr] gap-4 items-baseline group"
                style={{ borderLeft: "1px solid rgba(94,234,212,0.5)" }}
              >
                <div className="font-mono text-[18px]" style={{ color: "#64748B" }}>{l.n}</div>
                <div>
                  <div className="text-[17px] font-semibold" style={{ color: "#F1F5F9" }}>{l.name}</div>
                  <div className="mt-1 text-[14px]" style={{ color: "#64748B", lineHeight: 1.55 }}>{l.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* DASHBOARD */}
      <section id="dashboard" className="px-6 py-32 md:py-40">
        <div className="max-w-5xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              From audio to verdict in under 10 seconds.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center" style={{ color: "#64748B", fontSize: "0.95rem" }}>
              Illustrative readout of one flagged call — the neural detector carries the verdict.
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="mt-16 rounded-2xl p-8 md:p-12 grid md:grid-cols-2 gap-12 items-center"
              style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)" }}
            >
              <RiskGauge target={94} />
              <div className="space-y-4">
                {DASHBOARD_LAYERS.map((l, i) => (
                  <motion.div
                    key={l.name}
                    initial={{ opacity: 0, y: 8 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.4 }}
                    transition={{ duration: 0.5, delay: 0.5 + i * 0.12 }}
                    className="grid grid-cols-[140px_1fr_36px] items-center gap-4"
                  >
                    <div className="text-[12px]" style={{ color: "#F1F5F9" }}>{l.name}</div>
                    <div className="h-[2px] overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: `${l.v}%` }}
                        viewport={{ once: true, amount: 0.4 }}
                        transition={{ duration: 0.8, delay: 0.6 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
                        style={{ height: "100%", backgroundColor: "#5EEAD4" }}
                      />
                    </div>
                    <div className="font-mono text-[11px] text-right" style={{ color: "#64748B" }}>{l.v}</div>
                  </motion.div>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              {["99.2% acc · EER 1.6% · AUC 0.999", "real-time · 2s updates", "dual neural + content + channel", "explainable verdicts"].map((s) => (
                <div key={s} className="px-4 py-2 rounded-full font-mono text-[11px]"
                  style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)", color: "#64748B" }}
                >
                  {s}
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* LIVE DEMO */}
      <section id="demo" className="px-6 py-32 md:py-40">
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Drop any voice. Get a verdict.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center mx-auto" style={{ color: "#64748B", fontSize: "1rem", maxWidth: 560 }}>
              Upload a real audio file. All five detection layers run instantly and the scores you see are live.
            </p>
          </Reveal>
          <Reveal delay={0.15}>
            <div className="mt-14">
              <LiveDemo />
            </div>
          </Reveal>
        </div>
      </section>

      {/* LIVE MONITOR — real-time streaming + mic (Phase 3A/3B) */}
      <section id="monitor" className="px-6 py-32 md:py-40">
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Or monitor a live call as it happens.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center mx-auto" style={{ color: "#64748B", fontSize: "1rem", maxWidth: 560 }}>
              Stream from your microphone or a file. The risk score updates every few seconds as the call unfolds.
            </p>
          </Reveal>
          <Reveal delay={0.15}>
            <div className="mt-14">
              <LiveMonitor />
            </div>
          </Reveal>
        </div>
      </section>

      {/* DEMOS HUB — every live surface in one place, integration-forward */}
      <section id="demos" className="px-6 py-32 md:py-40">
        <div className="max-w-6xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Live demos. One integration.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center mx-auto" style={{ color: "#64748B", fontSize: "1rem", maxWidth: 620 }}>
              The same on-prem engine, tapped at every point a bank would wire it in — a SIPREC
              media-fork on the live call, a step-up voice-OTP, a 1:1 voiceprint, and the fraud console.
            </p>
          </Reveal>

          <div className="mt-14 grid gap-5 md:grid-cols-3">
            <DemoCard
              tag="ATTACK RANGE" tagColor="#5EEAD4" featured
              title="Mock bank vs. attacker"
              desc="Launch a THREAT.md attack at a mock bank, then flip the shield ON/OFF. Off: the money leaves. On: caught and escalated. The A/B that sells it."
              href="/range" cta="Open the range" delay={0}
            />
            <DemoCard
              tag="INTEGRATION" tagColor="#38BDF8"
              title="Live Call — SIPREC-style"
              desc="Two tabs: customer + bank agent. The agent side taps the call audio and the verdict lands on their screen mid-call — exactly how it drops into a contact centre."
              href="/call" cta="Open live call" delay={0.06}
            />
            <DemoCard
              tag="DETECT" tagColor="#38BDF8"
              title="Upload / stream detection"
              desc="Drop an audio file or stream your mic. All layers run live: dual neural core, APP-fraud, replay + quality gates — with the 10-second flag clock."
              href="#demo" cta="Try detection" delay={0.06}
            />
            <DemoCard
              tag="RURAL · ग्रामीण" tagColor="#F59E0B"
              title="Vernacular scam warning"
              desc="For villagers who can't read an OTP: the shield hears the coercion in Hindi and speaks a warning back — literacy-free, at the moment of risk. Turn sound on."
              href="/rural" cta="Hear it" delay={0.12}
            />
            <DemoCard
              tag="RURAL · बैंक मित्र" tagColor="#F59E0B"
              title="Bank Mitra verification"
              desc="In a branchless village the Business Correspondent IS the bank. Voiceprint the Mitra — a stranger fails, an AI clone is caught by the deepfake check."
              href="/mitra" cta="Verify a Mitra" delay={0.18}
            />
            <DemoCard
              tag="RURAL · भाषा" tagColor="#F59E0B"
              title="Language reach"
              desc="Deepfake detection is language-agnostic; the coercion layer covers major languages via Whisper and tribal dialects via a Bhashini / AI4Bharat adapter."
              href="/languages" cta="See coverage" delay={0.24}
            />
            <DemoCard
              tag="RURAL · ज़िला" tagColor="#F59E0B"
              title="District campaign alert"
              desc="Villagers rarely report — so one fraud voice sweeping a district is caught as a ring, blocklisted, and the customers it hasn't reached are warned proactively."
              href="/campaign" cta="See the sweep" delay={0.3}
            />
            <DemoCard
              tag="STEP-UP" tagColor="#38BDF8"
              title="Voice-OTP"
              desc="A flagged call escalates here: read a fresh one-time code aloud. A recording can't answer it; a clone that does still fails the deepfake + replay checks."
              href="/verify" cta="Run Voice-OTP" delay={0.18}
            />
            <DemoCard
              tag="IDENTITY" tagColor="#22C55E"
              title="1:1 Voiceprint"
              desc="Enroll once, then verify by reading digits. An ECAPA speaker embedding proves it's this customer — same-voice cosine 0.80 vs 0.15 for an impostor."
              href="/voiceprint" cta="Enroll & verify" delay={0.18}
            />
            <DemoCard
              tag="CONSOLE" tagColor="#A78BFA"
              title="Fraud console"
              desc="What the analyst opens: per-call evidence packs, fraud-campaign correlation, governance (TPR/FPR, drift, registry), Prometheus metrics."
              href={`${BACKEND}/cases`} cta="Open cases ↗" external delay={0.24}
            />
            <DemoCard
              tag="CONTRACT" tagColor="#64748B"
              title="One JSON verdict"
              desc="risk_score · alert_level · action · escalation · replay · campaign — the same contract to the agent UI and the decisioning engine. No rip-and-replace."
              href={`${BACKEND}/metrics`} cta="See metrics ↗" external delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* SIMULATION */}
      <section id="simulate" className="px-6 py-32 md:py-40">
        <div className="max-w-6xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Tested against the best cloning tools available.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center mx-auto" style={{ color: "#64748B", fontSize: "0.95rem", maxWidth: 560 }}>
              Illustrative scenarios — run the live demo above for real, on-the-spot scores.
            </p>
          </Reveal>

          <div className="mt-16 grid md:grid-cols-3 gap-5">
            <AttackCard
              title="Real Human Voice"
              score="08"
              color="#22C55E"
              verdict="PROTECTED"
              note="Neural core clear · channel trusted"
              breakdown={["Neural · 05", "Acoustic · 22", "APP-fraud · 04", "Replay · 06", "Action · MONITOR"]}
              delay={0}
            />
            <AttackCard
              title="ElevenLabs Clone"
              score="94"
              color="#FF4D6D"
              verdict="CRITICAL"
              note="Dual neural core flagged"
              breakdown={["Neural · 96", "Acoustic · 44", "APP-fraud · 08", "Replay · 12", "Action · BLOCK"]}
              delay={0.1}
            />
            <AttackCard
              title="Coached Customer"
              score="80"
              color="#F59E0B"
              verdict="HIGH RISK"
              note="Real voice — APP-fraud in the script"
              breakdown={["Neural · 06", "Acoustic · 19", "APP-fraud · 80", "Replay · 07", "Action · → HUMAN"]}
              delay={0.2}
            />
          </div>
        </div>
      </section>

      <footer className="px-6 py-10 border-t text-center" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
        <p className="text-[12px]" style={{ color: "#64748B" }}>
          Dhwani Kavach · Built for banking security · 2026
        </p>
      </footer>
    </div>
  );
}

function DemoCard({
  tag, tagColor, title, desc, href, cta, delay, featured, external,
}: {
  tag: string; tagColor: string; title: string; desc: string; href: string; cta: string;
  delay: number; featured?: boolean; external?: boolean;
}) {
  return (
    <motion.a
      href={href}
      {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.5, delay }}
      className="group flex flex-col rounded-2xl p-7 transition-colors duration-300"
      style={{
        backgroundColor: "#0F1117",
        border: `1px solid ${featured ? "rgba(94,234,212,0.35)" : "rgba(255,255,255,0.07)"}`,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = tagColor)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = featured ? "rgba(94,234,212,0.35)" : "rgba(255,255,255,0.07)")}
    >
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: tagColor }} />
        <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color: tagColor }}>{tag}</span>
        {featured && (
          <span className="ml-auto font-mono text-[9px] tracking-[0.15em] px-2 py-0.5 rounded-full"
            style={{ border: `1px solid ${tagColor}`, color: tagColor }}>PANEL FOCUS</span>
        )}
      </div>
      <div className="mt-5 text-[17px] font-semibold" style={{ color: "#F1F5F9" }}>{title}</div>
      <div className="mt-2.5 text-[13px] flex-1" style={{ color: "#64748B", lineHeight: 1.55 }}>{desc}</div>
      <div className="mt-6 font-mono text-[12px] inline-flex items-center gap-1.5 transition-colors"
        style={{ color: tagColor }}>
        {cta} <span className="transition-transform group-hover:translate-x-0.5">→</span>
      </div>
    </motion.a>
  );
}

function AttackCard({
  title, score, color, verdict, note, breakdown, delay,
}: {
  title: string; score: string; color: string; verdict: string; note: string; breakdown: string[]; delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.5, delay }}
      className="rounded-2xl p-7 transition-colors duration-300"
      style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = color)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)")}
    >
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-mono text-[10px] tracking-[0.2em]" style={{ color }}>{verdict}</span>
      </div>
      <div className="mt-6 text-[15px] font-medium" style={{ color: "#F1F5F9" }}>{title}</div>
      <div className="mt-2 font-mono font-bold leading-none" style={{ color, fontSize: 64 }}>{score}</div>
      <div className="mt-6 text-[13px]" style={{ color: "#64748B" }}>{note}</div>
      <div className="mt-6 pt-6 space-y-1.5 border-t" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
        {breakdown.map((b) => (
          <div key={b} className="font-mono text-[11px]" style={{ color: "#64748B" }}>{b}</div>
        ))}
      </div>
    </motion.div>
  );
}
