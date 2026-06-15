"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Reveal } from "./reveal"
import { Upload, Play, Square, CheckCircle2, AlertTriangle, XCircle, FileAudio } from "lucide-react"

type AlertLevel = "GREEN" | "AMBER" | "RED"

type Result = {
  risk_score: number
  alert_level: AlertLevel
  layer_breakdown: Record<string, number>
}

const VERDICT: Record<AlertLevel, { color: string; bg: string; icon: typeof CheckCircle2; label: string }> = {
  GREEN: { color: "text-safe",   bg: "bg-safe/15",   icon: CheckCircle2,  label: "Authentic"  },
  AMBER: { color: "text-cyan",   bg: "bg-cyan/15",   icon: AlertTriangle, label: "Suspicious" },
  RED:   { color: "text-threat", bg: "bg-threat/15", icon: XCircle,       label: "Deepfake"   },
}

const LAYERS = ["aasist", "mfcc", "breath", "phase", "liveness"] as const
const LAYER_LABELS: Record<string, string> = {
  aasist: "AASIST (neural)",
  mfcc: "MFCC / Spectral",
  breath: "Breath patterns",
  phase: "Phase coherence",
  liveness: "Liveness",
}

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const ACCEPT = ".wav,.mp3,.flac,.ogg,.webm,.m4a,audio/*"

export function SimulationSection() {
  const [file, setFile]           = useState<File | null>(null)
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [playing, setPlaying]     = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult]       = useState<Result | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [dragging, setDragging]   = useState(false)
  const audioRef   = useRef<HTMLAudioElement | null>(null)
  const inputRef   = useRef<HTMLInputElement>(null)

  // cleanup object URL on change
  useEffect(() => () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }, [objectUrl])

  function stopAudio() {
    audioRef.current?.pause()
    if (audioRef.current) audioRef.current.currentTime = 0
    setPlaying(false)
  }

  function clearFile() {
    stopAudio()
    setFile(null)
    setObjectUrl(null)
    setResult(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ""
  }

  const loadFile = useCallback(async (f: File) => {
    stopAudio()
    setResult(null)
    setError(null)
    setFile(f)
    setObjectUrl(URL.createObjectURL(f))

    // Send to backend immediately
    setAnalyzing(true)
    try {
      const form = new FormData()
      form.append("audio", f, f.name)
      const resp = await fetch(`${BACKEND}/api/analyze`, { method: "POST", body: form })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(`Server ${resp.status}: ${text.slice(0, 120)}`)
      }
      setResult(await resp.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAnalyzing(false)
    }
  }, [])

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) loadFile(f)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f && f.type.startsWith("audio/")) loadFile(f)
  }

  function togglePlay() {
    const a = audioRef.current
    if (!a) return
    if (playing) { a.pause(); setPlaying(false) }
    else         { a.play();  setPlaying(true)  }
  }

  return (
    <section id="simulate" className="relative px-6 py-32">
      <div className="mx-auto max-w-4xl">
        <Reveal>
          <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.25em] text-cyan">
            Live analysis
          </p>
          <h2 className="mx-auto max-w-3xl text-balance text-center font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            Drop any voice — get a verdict
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-pretty text-center leading-relaxed text-muted-foreground">
            Upload a real audio file. All five detection layers run on it instantly and the scores you see are live.
          </p>
        </Reveal>

        {/* Upload zone */}
        <Reveal delay={0.1}>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !file && inputRef.current?.click()}
            className={`glass mt-12 flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed p-10 transition-all
              ${dragging ? "border-cyan bg-cyan/10 scale-[1.01]" : "border-border hover:border-cyan/50 hover:bg-white/5"}
              ${file ? "cursor-default" : ""}`}
          >
            <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={onInputChange} />

            <AnimatePresence mode="wait">
              {!file ? (
                <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="flex flex-col items-center gap-3 text-center">
                  <Upload className={`h-10 w-10 transition-colors ${dragging ? "text-cyan" : "text-muted-foreground"}`} />
                  <p className="text-sm font-medium">{dragging ? "Release to analyze" : "Drop audio here or click to browse"}</p>
                  <p className="text-xs text-muted-foreground">WAV · MP3 · FLAC · OGG · WebM · M4A</p>
                </motion.div>
              ) : (
                <motion.div key="file" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="flex w-full flex-col gap-4">
                  {/* File info row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileAudio className="h-5 w-5 shrink-0 text-cyan" />
                      <span className="max-w-[280px] truncate text-sm font-medium">{file.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {(file.size / 1024).toFixed(0)} KB
                      </span>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); clearFile() }}
                      className="rounded-lg px-3 py-1 text-xs text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors">
                      Clear
                    </button>
                  </div>

                  {/* Audio player */}
                  {objectUrl && (
                    <div className="flex items-center gap-3">
                      <button onClick={(e) => { e.stopPropagation(); togglePlay() }}
                        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cyan/15 text-cyan hover:bg-cyan/25 transition-colors">
                        {playing ? <Square className="h-3.5 w-3.5 fill-current" /> : <Play className="h-3.5 w-3.5" />}
                      </button>
                      <audio
                        ref={audioRef}
                        src={objectUrl}
                        onEnded={() => setPlaying(false)}
                        className="h-8 w-full"
                        controls
                        style={{ colorScheme: "dark" }}
                      />
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </Reveal>

        {/* Results panel */}
        <AnimatePresence>
          {(analyzing || result || error) && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-strong mt-4 overflow-hidden rounded-3xl p-8"
            >
              <AnimatePresence mode="wait">
                {analyzing && <AnalyzingPanel key="analyzing" />}
                {!analyzing && result && <ResultPanel key="result" result={result} />}
                {!analyzing && error && <ErrorPanel key="error" message={error} />}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}

function AnalyzingPanel() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="flex flex-col items-center gap-5 py-4">
      <span className="font-mono text-sm text-cyan">Running all 5 layers…</span>
      <div className="flex flex-wrap justify-center gap-2">
        {["AASIST", "MFCC", "Breath", "Phase", "Liveness"].map((l, i) => (
          <motion.span key={l}
            className="rounded-md bg-cyan/15 px-3 py-1.5 text-xs text-cyan"
            initial={{ opacity: 0.3 }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.18 }}>
            {l}
          </motion.span>
        ))}
      </div>
      <div className="h-1 w-64 overflow-hidden rounded-full bg-secondary">
        <motion.div className="h-full bg-cyan" initial={{ width: "0%" }}
          animate={{ width: "100%" }} transition={{ duration: 3, ease: "linear" }} />
      </div>
    </motion.div>
  )
}

function ResultPanel({ result }: { result: Result }) {
  const meta = VERDICT[result.alert_level]
  const Icon = meta.icon
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="flex flex-col gap-6">
      {/* Verdict + score */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className={`inline-flex items-center gap-2 rounded-full ${meta.bg} px-4 py-2 ${meta.color}`}>
          <Icon className="h-5 w-5" />
          <span className="font-semibold">{meta.label}</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className={`font-heading text-5xl font-semibold tabular-nums ${meta.color}`}>
            {result.risk_score}
          </span>
          <span className="text-sm text-muted-foreground">/ 100 risk</span>
        </div>
      </div>

      {/* Layer breakdown */}
      <div className="grid gap-3">
        {LAYERS.map((key) => {
          const score = result.layer_breakdown[key] ?? 0
          const barColor = score >= 70 ? "bg-threat" : score >= 40 ? "bg-cyan" : "bg-safe"
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-xs text-muted-foreground">{LAYER_LABELS[key]}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
                <motion.div className={`h-full rounded-full ${barColor}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
              </div>
              <span className="w-8 shrink-0 text-right font-mono text-xs text-muted-foreground">
                {score}
              </span>
            </div>
          )
        })}
      </div>

      <p className="text-xs text-muted-foreground">
        AASIST carries 60% of the final score (trained classifier). Remaining layers are signal-processing heuristics.
      </p>
    </motion.div>
  )
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="flex flex-col items-center gap-3 py-4 text-center">
      <XCircle className="h-8 w-8 text-threat" />
      <p className="text-sm font-medium text-threat">Analysis failed</p>
      <p className="font-mono text-xs text-muted-foreground">{message}</p>
      <p className="text-xs text-muted-foreground">
        Make sure the backend is running:{" "}
        <code className="rounded bg-secondary px-1.5 py-0.5">cd backend && uvicorn app.main:app --reload</code>
      </p>
    </motion.div>
  )
}
