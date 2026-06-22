"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"
import { Reveal } from "./reveal"
import { Upload, CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react"
import { decodeTo16kMono, streamPcm, TARGET_SR } from "@/lib/audio-stream"
import { useWebSocket } from "@/lib/use-websocket"

type AlertLevel = "GREEN" | "AMBER" | "RED"
type Result = { risk_score: number; alert_level: AlertLevel; layer_breakdown: Record<string, number> }
type WsMsg = Result | { error: string }

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const WS_URL = BACKEND.replace(/^http/, "ws") + "/ws/analyze"

const LAYERS = ["aasist", "mfcc", "breath", "phase", "liveness"] as const
const LAYER_LABELS: Record<string, string> = {
  aasist: "AASIST", mfcc: "MFCC", breath: "Breath", phase: "Phase", liveness: "Liveness",
}
const VERDICT: Record<AlertLevel, { color: string; track: string; icon: typeof CheckCircle2; label: string }> = {
  GREEN: { color: "text-safe",   track: "text-safe",   icon: CheckCircle2,  label: "Authentic" },
  AMBER: { color: "text-cyan",   track: "text-cyan",   icon: AlertTriangle, label: "Suspicious" },
  RED:   { color: "text-threat", track: "text-threat", icon: XCircle,       label: "Deepfake detected" },
}

export function DashboardSection() {
  const [result, setResult] = useState<Result | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const stopVisualRef = useRef<(() => void) | null>(null)

  const onMessage = useCallback((msg: WsMsg) => {
    if ("error" in msg) setError(msg.error)
    else setResult(msg)
  }, [])
  const { status, send, reconnect } = useWebSocket<WsMsg>(WS_URL, onMessage)

  useEffect(() => () => { stopVisualRef.current?.(); abortRef.current?.abort() }, [])

  const analyze = useCallback(async (file: File) => {
    stopVisualRef.current?.()
    abortRef.current?.abort()
    setError(null); setResult(null); setFileName(file.name)
    reconnect()
    try {
      const pcm = await decodeTo16kMono(file)
      stopVisualRef.current = startSpectrogram(pcm, canvasRef.current)
      setStreaming(true)
      abortRef.current = new AbortController()
      await streamPcm(pcm, send, { signal: abortRef.current.signal })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setStreaming(false)
    }
  }, [reconnect, send])

  const verdict = result ? VERDICT[result.alert_level] : null
  const Icon = verdict?.icon ?? Loader2
  const risk = result?.risk_score ?? 0
  const radius = 120
  const circumference = Math.PI * radius
  const dash = (risk / 100) * circumference

  return (
    <section id="dashboard" className="relative px-6 py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.25em] text-cyan">
            Real-time intelligence
          </p>
          <h2 className="mx-auto max-w-3xl text-balance text-center font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            The threat dashboard, scoring as you watch
          </h2>
          <p className="mx-auto mt-5 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <StatusDot status={status} />
            {status === "open" ? "Live socket connected" : status === "connecting" ? "Connecting to detector…" : "Detector offline — start the backend"}
          </p>
        </Reveal>

        {/* Stream control */}
        <Reveal delay={0.05}>
          <div className="mt-10 flex justify-center">
            <button
              onClick={() => inputRef.current?.click()}
              disabled={streaming}
              className="inline-flex items-center gap-2 rounded-full bg-cyan/15 px-5 py-2.5 text-sm font-medium text-cyan transition-colors hover:bg-cyan/25 disabled:opacity-50"
            >
              {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {streaming ? `Streaming ${fileName ?? ""}…` : "Stream an audio file through the pipeline"}
            </button>
            <input
              ref={inputRef} type="file" accept=".wav,.mp3,.flac,.ogg,.webm,.m4a,audio/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) analyze(f); e.target.value = "" }}
            />
          </div>
        </Reveal>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          {/* Live risk gauge */}
          <Reveal>
            <div className="glass-strong flex h-full flex-col items-center justify-center rounded-3xl p-10">
              <span className="mb-2 text-xs uppercase tracking-[0.25em] text-muted-foreground">
                Deepfake risk score
              </span>
              <div className="relative">
                <svg width="280" height="170" viewBox="0 0 280 170">
                  <path d="M 20 150 A 120 120 0 0 1 260 150" fill="none" stroke="currentColor"
                    className="text-secondary" strokeWidth="16" strokeLinecap="round" />
                  <motion.path d="M 20 150 A 120 120 0 0 1 260 150" fill="none" stroke="currentColor"
                    className={verdict?.track ?? "text-muted-foreground"} strokeWidth="16" strokeLinecap="round"
                    strokeDasharray={`${dash} ${circumference}`}
                    animate={{ strokeDasharray: `${dash} ${circumference}` }}
                    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} />
                </svg>
                <div className="absolute inset-x-0 bottom-2 flex flex-col items-center">
                  <span className={`font-heading text-6xl font-semibold tabular-nums ${verdict?.color ?? "text-muted-foreground"}`}>
                    {risk}
                  </span>
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">/ 100 risk</span>
                </div>
              </div>
              <div className={`mt-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${verdict ? `${verdict.color} bg-current/10` : "text-muted-foreground"}`}>
                <Icon className={`h-4 w-4 ${!result && streaming ? "animate-spin" : ""}`} />
                {result ? verdict!.label : streaming ? "Analyzing window…" : "Waiting for audio"}
              </div>
            </div>
          </Reveal>

          {/* Live spectrogram (step 28) */}
          <Reveal delay={0.1}>
            <div className="glass-strong flex h-full flex-col rounded-3xl p-6">
              <span className="mb-3 text-sm font-medium">Live spectrogram</span>
              <canvas ref={canvasRef} width={512} height={180}
                className="w-full flex-1 rounded-xl bg-secondary/40" />
              <span className="mt-3 text-xs text-muted-foreground">
                128-band mel · {TARGET_SR / 1000} kHz · 10s window, 5s hop
              </span>
            </div>
          </Reveal>
        </div>

        {/* Live layer breakdown (step 30) */}
        <Reveal delay={0.15}>
          <div className="glass-strong mt-6 grid gap-4 rounded-3xl p-8 sm:grid-cols-2 lg:grid-cols-5">
            {LAYERS.map((key) => {
              const score = result?.layer_breakdown[key] ?? 0
              const bar = score >= 70 ? "bg-threat" : score >= 40 ? "bg-cyan" : "bg-safe"
              return (
                <div key={key} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{LAYER_LABELS[key]}</span>
                    <span className="font-mono text-foreground">{score}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                    <motion.div className={`h-full rounded-full ${bar}`} animate={{ width: `${score}%` }}
                      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} />
                  </div>
                </div>
              )
            })}
          </div>
        </Reveal>

        {error && (
          <p className="mt-4 text-center font-mono text-xs text-threat">{error}</p>
        )}
      </div>
    </section>
  )
}

function StatusDot({ status }: { status: "connecting" | "open" | "closed" }) {
  const c = status === "open" ? "bg-safe" : status === "connecting" ? "bg-cyan" : "bg-threat"
  return <span className={`h-2 w-2 rounded-full ${c} ${status !== "closed" ? "animate-pulse" : ""}`} />
}

/** Play the PCM through an AnalyserNode and draw a scrolling 128-band spectrogram. */
function startSpectrogram(pcm: Float32Array, canvas: HTMLCanvasElement | null): () => void {
  if (!canvas) return () => {}
  const ctx = canvas.getContext("2d")
  if (!ctx) return () => {}

  const w = canvas.width, h = canvas.height
  ctx.clearRect(0, 0, w, h)

  const AC = (window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)
  const ac = new AC()
  const buffer = ac.createBuffer(1, pcm.length, TARGET_SR)
  buffer.copyToChannel(pcm, 0)
  const src = ac.createBufferSource()
  src.buffer = buffer
  const analyser = ac.createAnalyser()
  analyser.fftSize = 256 // -> 128 frequency bins
  src.connect(analyser)
  analyser.connect(ac.destination)
  src.start()

  const bins = analyser.frequencyBinCount
  const data = new Uint8Array(bins)
  let raf = 0
  let stopped = false

  const draw = () => {
    if (stopped) return
    raf = requestAnimationFrame(draw)
    analyser.getByteFrequencyData(data)
    const img = ctx.getImageData(1, 0, w - 1, h)
    ctx.putImageData(img, 0, 0)
    const colH = h / bins + 1
    for (let i = 0; i < bins; i++) {
      const v = data[i] / 255
      ctx.fillStyle = `hsl(${190 - v * 130}, 85%, ${8 + v * 50}%)`
      ctx.fillRect(w - 1, h - (i / bins) * h, 1, colH)
    }
  }
  draw()

  const stop = () => { stopped = true; cancelAnimationFrame(raf); try { src.stop() } catch {} ; ac.close() }
  src.onended = stop
  return stop
}
