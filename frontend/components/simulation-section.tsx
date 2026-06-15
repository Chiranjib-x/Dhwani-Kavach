"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Reveal } from "./reveal"
import { Play, Square, CheckCircle2, AlertTriangle, XCircle } from "lucide-react"

type Verdict = "authentic" | "suspicious" | "deepfake"

type Sample = {
  id: string
  label: string
  source: string
  file: string
}

const samples: Sample[] = [
  {
    id: "real",
    label: "Real Voice",
    source: "Live human customer",
    file: "/samples/real_voice.wav",
  },
  {
    id: "eleven",
    label: "ElevenLabs Clone",
    source: "Commercial TTS clone",
    file: "/samples/tts_clone.wav",
  },
  {
    id: "custom",
    label: "Custom Deepfake",
    source: "Bespoke voice model",
    file: "/samples/custom_deepfake.wav",
  },
]

type Result = {
  risk_score: number
  alert_level: "GREEN" | "AMBER" | "RED"
  layer_breakdown: Record<string, number>
}

const verdictMeta: Record<
  "GREEN" | "AMBER" | "RED",
  { color: string; bg: string; icon: typeof CheckCircle2; label: Verdict }
> = {
  GREEN:  { color: "text-safe",   bg: "bg-safe/15",   icon: CheckCircle2,   label: "authentic"  },
  AMBER:  { color: "text-cyan",   bg: "bg-cyan/15",   icon: AlertTriangle,  label: "suspicious" },
  RED:    { color: "text-threat", bg: "bg-threat/15", icon: XCircle,        label: "deepfake"   },
}

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const LAYERS = ["aasist", "mfcc", "breath", "phase", "liveness"] as const

export function SimulationSection() {
  const [active, setActive]       = useState<string | null>(null)
  const [playing, setPlaying]     = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult]       = useState<Result | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  function stopCurrent() {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    setPlaying(false)
  }

  async function run(sample: Sample) {
    stopCurrent()
    setActive(sample.id)
    setResult(null)
    setError(null)

    // Play audio
    const audio = new Audio(sample.file)
    audioRef.current = audio
    audio.onended = () => setPlaying(false)
    audio.play().catch(() => {})
    setPlaying(true)

    // Fetch audio bytes and send to backend
    setAnalyzing(true)
    try {
      const res  = await fetch(sample.file)
      const blob = await res.blob()
      const form = new FormData()
      form.append("audio", blob, "sample.wav")

      const resp = await fetch(`${BACKEND}/api/analyze`, {
        method: "POST",
        body: form,
      })
      if (!resp.ok) throw new Error(`Backend error ${resp.status}`)
      const data: Result = await resp.json()
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to reach backend")
    } finally {
      setAnalyzing(false)
    }
  }

  // cleanup on unmount
  useEffect(() => () => { audioRef.current?.pause() }, [])

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
            Click a sample — hear it play and watch Dhwani-Kavach score it live across all five layers.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-4 md:grid-cols-3">
          {samples.map((s, i) => (
            <Reveal key={s.id} delay={i * 0.1}>
              <button
                onClick={() => active === s.id && playing ? stopCurrent() : run(s)}
                className={`glass group w-full rounded-2xl p-6 text-left transition-all hover:-translate-y-1 ${
                  active === s.id ? "ring-2 ring-cyan" : ""
                }`}
              >
                <div className="mb-4 flex items-center justify-between">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/15 text-cyan transition-transform group-hover:scale-110">
                    {active === s.id && playing
                      ? <Square className="h-4 w-4 fill-current" />
                      : <Play  className="h-4 w-4" />}
                  </span>
                  <WaveBars active={active === s.id && playing} />
                </div>
                <h3 className="font-semibold">{s.label}</h3>
                <p className="text-xs text-muted-foreground">{s.source}</p>
              </button>
            </Reveal>
          ))}
        </div>

        {/* analysis output */}
        <Reveal delay={0.15}>
          <div className="glass-strong relative mt-6 min-h-[260px] overflow-hidden rounded-3xl p-8">
            <AnimatePresence mode="wait">
              {!active && (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-[180px] items-center justify-center text-sm text-muted-foreground"
                >
                  Select a voice sample above to begin analysis.
                </motion.div>
              )}

              {active && analyzing && (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-[180px] flex-col items-center justify-center gap-4"
                >
                  <span className="font-mono text-sm text-cyan">
                    Analyzing {samples.find(s => s.id === active)?.label}…
                  </span>
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
                      transition={{ duration: 2.5, ease: "linear" }}
                    />
                  </div>
                </motion.div>
              )}

              {active && !analyzing && result && (
                <ResultPanel key={active + result.risk_score} result={result} />
              )}

              {active && !analyzing && error && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex h-[180px] flex-col items-center justify-center gap-2"
                >
                  <XCircle className="h-8 w-8 text-threat" />
                  <p className="text-sm text-threat">Backend unreachable — start the API server first.</p>
                  <p className="font-mono text-xs text-muted-foreground">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function ResultPanel({ result }: { result: Result }) {
  const meta = verdictMeta[result.alert_level]
  const Icon = meta.icon
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex flex-col gap-6"
    >
      {/* verdict row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className={`inline-flex items-center gap-2 rounded-full ${meta.bg} px-4 py-2 ${meta.color}`}>
          <Icon className="h-5 w-5" />
          <span className="font-semibold capitalize">{meta.label}</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className={`font-heading text-5xl font-semibold tabular-nums ${meta.color}`}>
            {result.risk_score}
          </span>
          <span className="text-sm text-muted-foreground">/ 100 risk</span>
        </div>
      </div>

      {/* layer bars */}
      <div className="grid gap-2">
        {LAYERS.map((key) => {
          const score = result.layer_breakdown[key] ?? 0
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-16 shrink-0 text-xs capitalize text-muted-foreground">{key}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
                <motion.div
                  className={`h-full rounded-full ${score >= 70 ? "bg-threat" : score >= 40 ? "bg-cyan" : "bg-safe"}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
              <span className="w-8 shrink-0 text-right font-mono text-xs text-muted-foreground">
                {score}
              </span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

function WaveBars({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-0.5">
      {[6, 12, 8, 16, 10, 14, 7].map((h, i) => (
        <motion.span
          key={i}
          className="w-0.5 rounded-full bg-cyan/60"
          style={{ height: h }}
          animate={active ? { scaleY: [0.4, 1, 0.4] } : { scaleY: 0.4 }}
          transition={{ duration: 1, repeat: active ? Number.POSITIVE_INFINITY : 0, delay: i * 0.1 }}
        />
      ))}
    </div>
  )
}
