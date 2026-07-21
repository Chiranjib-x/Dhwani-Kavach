import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import Nav from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import LiveDemo from "@/components/LiveDemo";
import LiveMonitor from "@/components/LiveMonitor";
import RiskGauge from "@/components/RiskGauge";

const HeroShield = lazy(() => import("@/components/HeroShield"));

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
  { n: "01", name: "Dual Neural Core", desc: "Two independent XLS-R detectors trained on different clone families cross-check every window" },
  { n: "02", name: "Spectral Biometrics", desc: "MFCC, jitter, shimmer the vocal tract can't fake" },
  { n: "03", name: "Breath Pattern", desc: "Real speech breathes irregularly. Synthesis doesn't." },
  { n: "04", name: "Phase Coherence", desc: "Every synthesis model leaves phase seams in the math" },
  { n: "05", name: "Active Liveness", desc: "A live challenge only a present human can answer" },
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
  { name: "Neural detector", v: 96 },
  { name: "Spectral Biometrics", v: 43 },
  { name: "Breath Pattern", v: 38 },
  { name: "Phase Coherence", v: 51 },
  { name: "Active Liveness", v: 88 },
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
          <p className="mt-6 mx-auto" style={{ color: "#64748B", fontSize: "1.1rem", maxWidth: 540, lineHeight: 1.5 }}>
            Dhwani Kavach detects AI-cloned voices on live banking calls — before the fraud happens.
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
              {["~95% on modern fakes", "real-time · 2s updates", "5 detection layers", "explainable verdicts"].map((s) => (
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
              note="Neural detector clear"
              breakdown={["Neural · 05", "Spectral · 22", "Breath · 72", "Phase · 31", "Liveness · 18"]}
              delay={0}
            />
            <AttackCard
              title="ElevenLabs Clone"
              score="94"
              color="#FF4D6D"
              verdict="CRITICAL"
              note="Neural detector flagged"
              breakdown={["Neural · 96", "Spectral · 44", "Breath · 75", "Phase · 49", "Liveness · 80"]}
              delay={0.1}
            />
            <AttackCard
              title="Custom Deepfake"
              score="78"
              color="#F59E0B"
              verdict="HIGH RISK"
              note="Neural detector — borderline"
              breakdown={["Neural · 77", "Spectral · 51", "Breath · 73", "Phase · 58", "Liveness · 66"]}
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
