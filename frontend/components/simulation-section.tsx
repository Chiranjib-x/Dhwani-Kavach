"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Reveal } from "./reveal"
import { Play, CheckCircle2, AlertTriangle, XCircle } from "lucide-react"

type Sample = {
  id: string
  label: string
  source: string
  verdict: "authentic" | "suspicious" | "deepfake"
  score: number
  note: string
}

const samples: Sample[] = [
  {
    id: "real",
    label: "Real Voice",
    source: "Live human customer",
    verdict: "authentic",
    score: 3,
    note: "Natural breath cadence and coherent phase. Cleared instantly.",
  },
  {
    id: "eleven",
    label: "ElevenLabs Clone",
    source: "Commercial TTS clone",
    verdict: "deepfake",
    score: 91,
    note: "Cepstral smearing + absent micro-pauses. Flagged across 4 layers.",
  },
  {
    id: "custom",
    label: "Custom Deepfake",
    source: "Bespoke voice model",
    verdict: "deepfake",
    score: 97,
    note: "Phase incoherence and failed liveness probe. Transaction blocked.",
  },
]

const verdictMeta = {
  authentic: { color: "text-safe", bg: "bg-safe/15", icon: CheckCircle2, label: "Authentic" },
  suspicious: { color: "text-cyan", bg: "bg-cyan/15", icon: AlertTriangle, label: "Suspicious" },
  deepfake: { color: "text-threat", bg: "bg-threat/15", icon: XCircle, label: "Deepfake" },
}

export function SimulationSection() {
  const [active, setActive] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const current = samples.find((s) => s.id === active)

  function run(id: string) {
    setActive(id)
    setAnalyzing(true)
  }

  useEffect(() => {
    if (!analyzing) return
    const t = setTimeout(() => setAnalyzing(false), 1800)
    return () => clearTimeout(t)
  }, [analyzing, active])

  return (
    <section id="simulate" className="relative px-6 py-32">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.25em] text-cyan">
            Attack simulation
          </p>
          <h2 className="mx-auto max-w-3xl text-balance text-center font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            Put a voice on trial
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-center leading-relaxed text-muted-foreground">
            Select a sample and watch Dhwani-Kavach analyze it through all five layers in real time.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-4 md:grid-cols-3">
          {samples.map((s, i) => (
            <Reveal key={s.id} delay={i * 0.1}>
              <button
                onClick={() => run(s.id)}
                className={`glass group w-full rounded-2xl p-6 text-left transition-all hover:-translate-y-1 ${
                  active === s.id ? "ring-2 ring-cyan" : ""
                }`}
              >
                <div className="mb-4 flex items-center justify-between">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/15 text-cyan transition-transform group-hover:scale-110">
                    <Play className="h-4 w-4" />
                  </span>
                  <WaveBars />
                </div>
                <h3 className="font-semibold">{s.label}</h3>
                <p className="text-xs text-muted-foreground">{s.source}</p>
              </button>
            </Reveal>
          ))}
        </div>

        {/* analysis output */}
        <Reveal delay={0.15}>
          <div className="glass-strong relative mt-6 min-h-[220px] overflow-hidden rounded-3xl p-8">
            <AnimatePresence mode="wait">
              {!current && (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-[160px] items-center justify-center text-sm text-muted-foreground"
                >
                  Select a voice sample above to begin analysis.
                </motion.div>
              )}

              {current && analyzing && (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-[160px] flex-col items-center justify-center gap-4"
                >
                  <span className="font-mono text-sm text-cyan">Analyzing {current.label}…</span>
                  <div className="flex gap-2">
                    {["AASIST", "MFCC", "Breath", "Phase", "Liveness"].map((l, i) => (
                      <motion.span
                        key={l}
                        className="rounded-md bg-cyan/15 px-3 py-1.5 text-xs text-cyan"
                        initial={{ opacity: 0.3 }}
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Number.POSITIVE_INFINITY, delay: i * 0.18 }}
                      >
                        {l}
                      </motion.span>
                    ))}
                  </div>
                  <div className="h-1 w-64 overflow-hidden rounded-full bg-secondary">
                    <motion.div
                      className="h-full bg-cyan"
                      initial={{ width: "0%" }}
                      animate={{ width: "100%" }}
                      transition={{ duration: 1.8, ease: "linear" }}
                    />
                  </div>
                </motion.div>
              )}

              {current && !analyzing && <Result key={current.id} sample={current} />}
            </AnimatePresence>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Result({ sample }: { sample: Sample }) {
  const meta = verdictMeta[sample.verdict]
  const Icon = meta.icon
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center gap-5 text-center"
    >
      <div className={`inline-flex items-center gap-2 rounded-full ${meta.bg} px-4 py-2 ${meta.color}`}>
        <Icon className="h-5 w-5" />
        <span className="font-semibold">{meta.label}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`font-heading text-5xl font-semibold tabular-nums ${meta.color}`}>
          {sample.score}
        </span>
        <span className="text-sm text-muted-foreground">/ 100 risk</span>
      </div>
      <p className="max-w-md text-sm leading-relaxed text-muted-foreground">{sample.note}</p>
    </motion.div>
  )
}

function WaveBars() {
  return (
    <div className="flex items-end gap-0.5">
      {[6, 12, 8, 16, 10, 14, 7].map((h, i) => (
        <motion.span
          key={i}
          className="w-0.5 rounded-full bg-cyan/60"
          style={{ height: h }}
          animate={{ scaleY: [0.4, 1, 0.4] }}
          transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY, delay: i * 0.1 }}
        />
      ))}
    </div>
  )
}
