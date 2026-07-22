import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import Nav from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import VoiceVerify from "@/components/VoiceVerify";

const HeroShield = lazy(() => import("@/components/HeroShield"));

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dhwani Kavach — Voice Identity Verification" },
      { name: "description", content: "Prove it's you, live, right now. Enroll a customer's voice once, then verify with a one-time spoken code checked by four independent gates: quality, phrase, liveness and voiceprint match." },
    ],
  }),
  component: Index,
});

// The four gates we actually run (see MASTER-PLAN.md). Every verification passes
// through all four; the first failing gate stops it, with a human-readable reason.
const GATES = [
  { n: "01", name: "Quality", desc: "Is the audio even worth judging? Mic level, noise and clipping — it abstains instead of guessing when the line is too poor." },
  { n: "02", name: "Phrase", desc: "A fresh one-time digit code, read live. Kills every replay and every pre-recorded clone — they carry the wrong digits." },
  { n: "03", name: "Liveness", desc: "A neural anti-spoof model trained on synthetic-speech artifacts decides live human vs TTS/voice-clone." },
  { n: "04", name: "Voiceprint match", desc: "An ECAPA speaker embedding, matched 1:1 against the enrolled customer. Genuine ~0.6–0.8, impostor <0.2." },
];

const THREATS = [
  { n: "01", t: "Impostor", d: "A stranger calls in reading the right code — but the voiceprint doesn't match the customer. Rejected." },
  { n: "02", t: "Replay", d: "A recording of the real customer — but it says last time's digits, not this session's. Dead on arrival." },
  { n: "03", t: "Live clone", d: "A real-time deepfake reading the code — flagged by liveness, then rate-limited and stepped up to OTP + agent." },
];

// Illustrative gate readout for ONE genuine verification (not accuracy stats) —
// measured live in the demo below.
const GATE_READOUT = [
  { name: "Quality", v: "clean · 4.2s", ok: true },
  { name: "Phrase", v: "472903 ok", ok: true },
  { name: "Liveness", v: "live 94%", ok: true },
  { name: "Voiceprint match", v: "0.61", ok: true },
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
            VOICE IDENTITY VERIFICATION
          </p>
          <h1 className="mt-6 font-bold mx-auto"
            style={{ color: "#F1F5F9", fontSize: "clamp(2.5rem, 5vw, 4.5rem)", maxWidth: 700, lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            Prove it's you. Live. Right now.
          </h1>
          <p className="mt-6 mx-auto" style={{ color: "#64748B", fontSize: "1.1rem", maxWidth: 560, lineHeight: 1.5 }}>
            Others ask <i>"is this voice AI?"</i>. We answer <i>"is this voice <b style={{ color: "#94a3b8" }}>you</b>?"</i> —
            enroll once, then confirm with a one-time spoken code checked by four independent gates.
          </p>
          <div className="mt-10">
            <a href="#demo"
              className="inline-flex items-center gap-2 rounded-full px-5 py-2 text-[13px] font-medium transition-colors duration-200"
              style={{ border: "1px solid #5EEAD4", color: "#5EEAD4", backgroundColor: "transparent" }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "#5EEAD4"; e.currentTarget.style.color = "#08090C"; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "transparent"; e.currentTarget.style.color = "#5EEAD4"; }}>
              Try it now →
            </a>
          </div>
        </div>
      </section>

      {/* THREAT */}
      <section id="threat" className="px-6 py-32 md:py-40">
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em", maxWidth: 720 }}>
              A cloned voice can fool a human. It can't pass all four gates.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4" style={{ color: "#64748B", fontSize: "1rem", maxWidth: 640 }}>
              No single fingerprint is un-cloneable — a good clone imitates exactly what a voiceprint measures.
              Security comes from the layers, each stopping a different attack.
            </p>
          </Reveal>

          <div className="mt-14 border-t" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
            {THREATS.map((row, i) => (
              <motion.div key={row.n}
                initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ duration: 0.5, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] }}
                className="grid grid-cols-[auto_1fr] md:grid-cols-[80px_220px_1fr] gap-x-6 md:gap-x-10 gap-y-2 py-8 border-b"
                style={{ borderColor: "rgba(255,255,255,0.07)" }}>
                <div className="font-mono text-[13px]" style={{ color: "#5EEAD4" }}>{row.n}</div>
                <div className="text-[18px] md:text-[20px] font-semibold col-span-1" style={{ color: "#F1F5F9" }}>{row.t}</div>
                <div className="col-span-2 md:col-span-1 text-[15px]" style={{ color: "#64748B", lineHeight: 1.55 }}>{row.d}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FOUR GATES */}
      <section id="defense" className="px-6 py-32 md:py-40">
        <div className="max-w-[680px] mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Four gates. One verdict.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center" style={{ color: "#64748B", fontSize: "1rem" }}>
              A verification passes through all four in order. The first that fails stops it — with a reason
              a customer can act on. Borderline cases step up to OTP + agent; we never hard-reject a genuine caller.
            </p>
          </Reveal>

          <div className="mt-16 space-y-1">
            {GATES.map((l, i) => (
              <motion.div key={l.n}
                initial={{ opacity: 0, x: -8 }} whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.6 }} transition={{ duration: 0.5, delay: i * 0.08 }}
                className="relative pl-6 py-5 grid grid-cols-[56px_1fr] gap-4 items-baseline"
                style={{ borderLeft: "1px solid rgba(94,234,212,0.5)" }}>
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

      {/* LIVE DEMO */}
      <section id="demo" className="px-6 py-32 md:py-40">
        <div className="max-w-[560px] mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              Enroll, then verify. Live.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center mx-auto" style={{ color: "#64748B", fontSize: "1rem", maxWidth: 500 }}>
              Enroll a user id with three short clips, then verify by reading a one-time code aloud.
              Every gate score you see is live.
            </p>
          </Reveal>
          <Reveal delay={0.15}>
            <div className="mt-12"><VoiceVerify /></div>
          </Reveal>
        </div>
      </section>

      {/* GATE READOUT */}
      <section id="dashboard" className="px-6 py-32 md:py-40">
        <div className="max-w-3xl mx-auto">
          <Reveal>
            <h2 className="font-bold tracking-tight text-center" style={{ color: "#F1F5F9", fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)", lineHeight: 1.2, letterSpacing: "-0.02em" }}>
              From voice to verdict in seconds.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 text-center" style={{ color: "#64748B", fontSize: "0.95rem" }}>
              Illustrative readout of one genuine verification — run the demo above for real, on-the-spot scores.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="mt-14 rounded-2xl p-8 md:p-10" style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)" }}>
              <div className="grid gap-4">
                {GATE_READOUT.map((l, i) => (
                  <motion.div key={l.name}
                    initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.4 }} transition={{ duration: 0.5, delay: 0.2 + i * 0.12 }}
                    className="grid grid-cols-[1fr_auto] items-center gap-4 pb-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                    <div className="text-[14px]" style={{ color: "#F1F5F9" }}>{l.name}</div>
                    <div className="font-mono text-[12px]" style={{ color: l.ok ? "#22C55E" : "#FF4D6D" }}>{l.v}</div>
                  </motion.div>
                ))}
                <div className="mt-2 text-center font-extrabold text-[22px]" style={{ color: "#22C55E" }}>ACCEPT</div>
              </div>
            </div>
          </Reveal>
          <Reveal delay={0.2}>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              {["4-gate cascade", "~2–5s on CPU", "1:1 verification", "explainable reasons", "step-up, never lock out"].map((s) => (
                <div key={s} className="px-4 py-2 rounded-full font-mono text-[11px]"
                  style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)", color: "#64748B" }}>
                  {s}
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="px-6 py-10 border-t text-center" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
        <p className="text-[12px]" style={{ color: "#64748B" }}>
          Dhwani Kavach · Voice identity verification for banking · 2026
        </p>
      </footer>
    </div>
  );
}
