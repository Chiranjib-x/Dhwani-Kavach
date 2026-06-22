"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Reveal } from "./reveal"
import { Upload, Mic, Square, CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react"
import { decodeTo16kMono, streamPcm, TARGET_SR } from "@/lib/audio-stream"
import { useWebSocket } from "@/lib/use-websocket"
import { useMicStream } from "@/lib/use-mic-stream"

type AlertLevel = "GREEN" | "AMBER" | "RED"
type Result = { risk_score: number; alert_level: AlertLevel; layer_breakdown: Record<string, number> }
type WsMsg = Result | { error: string }
type Alert = { id: number; time: string; risk: number; level: AlertLevel; layer: string }

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const WS_URL = BACKEND.replace(/^http/, "ws") + "/ws/analyze"

const LAYERS = ["aasist", "mfcc", "breath", "phase", "liveness"] as const
const LAYER_LABELS: Record<string, string> = {
  aasist: "AASIST", mfcc: "MFCC", breath: "Breath", phase: "Phase", liveness: "Liveness",
}
const VERDICT: Record<AlertLevel, { color: string; icon: typeof CheckCircle2; label: string }> = {
  GREEN: { color: "text-safe",   icon: CheckCircle2,  label: "Authentic" },
  AMBER: { color: "text-cyan",   icon: AlertTriangle, label: "Suspicious" },
  RED:   { color: "text-threat", icon: XCircle,       label: "Deepfake detected" },
}

export function DashboardSection() {
  const [result, setResult] = useState<Result | null>(null)
  const [mode, setMode] = useState<"idle" | "file" | "mic">("idle")
  const [fileName, setFileName] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const stopVisualRef = useRef<(() => void) | null>(null)
  const seq = useRef(0)

  const onMessage = useCallback((msg: WsMsg) => {
    if ("error" in msg) { setError(msg.error); return }
    setResult(msg)
    setAlerts((a) => [{
      id: ++seq.current, time: new Date().toLocaleTimeString(),
      risk: msg.risk_score, level: msg.alert_level, layer: topLayer(msg.layer_breakdown),
    }, ...a].slice(0, 20))
  }, [])
  const { status, send, reconnect } = useWebSocket<WsMsg>(WS_URL, onMessage)
  const mic = useMicStream(send)

  const cleanup = useCallback(() => {
    stopVisualRef.current?.(); stopVisualRef.current = null
    abortRef.current?.abort()
    mic.stop()
  }, [mic])
  useEffect(() => cleanup, [cleanup])

  const analyzeFile = useCallback(async (file: File) => {
    cleanup(); setError(null); setResult(null); setFileName(file.name); setMode("file")
    reconnect()
    try {
      const pcm = await decodeTo16kMono(file)
      stopVisualRef.current = playAndVisualize(pcm, canvasRef.current)
      abortRef.current = new AbortController()
      await streamPcm(pcm, send, { signal: abortRef.current.signal })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setMode("idle")
    }
  }, [cleanup, reconnect, send])

  const toggleMic = useCallback(async () => {
    if (mode === "mic") { cleanup(); setMode("idle"); return }
    cleanup(); setError(null); setResult(null); setMode("mic")
    reconnect()
    try {
      const analyser = await mic.start()
      stopVisualRef.current = renderSpectrogram(canvasRef.current, analyser)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setMode("idle")
    }
  }, [mode, cleanup, reconnect, mic])

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

        {/* Controls */}
        <Reveal delay={0.05}>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <button onClick={() => inputRef.current?.click()} disabled={mode !== "idle"}
              className="inline-flex items-center gap-2 rounded-full bg-cyan/15 px-5 py-2.5 text-sm font-medium text-cyan transition-colors hover:bg-cyan/25 disabled:opacity-50">
              {mode === "file" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {mode === "file" ? `Streaming ${fileName ?? ""}…` : "Stream an audio file"}
            </button>
            <button onClick={toggleMic} disabled={mode === "file"}
              className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 ${mode === "mic" ? "bg-threat/20 text-threat hover:bg-threat/30" : "bg-cyan/15 text-cyan hover:bg-cyan/25"}`}>
              {mode === "mic" ? <Square className="h-4 w-4 fill-current" /> : <Mic className="h-4 w-4" />}
              {mode === "mic" ? "Stop microphone" : "Use microphone (live)"}
            </button>
            <input ref={inputRef} type="file" accept=".wav,.mp3,.flac,.ogg,.webm,.m4a,audio/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) analyzeFile(f); e.target.value = "" }} />
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
                    className={verdict?.color ?? "text-muted-foreground"} strokeWidth="16" strokeLinecap="round"
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
                <Icon className={`h-4 w-4 ${!result && mode !== "idle" ? "animate-spin" : ""}`} />
                {result ? verdict!.label : mode !== "idle" ? "Analyzing window…" : "Waiting for audio"}
              </div>
            </div>
          </Reveal>

          {/* Live spectrogram */}
          <Reveal delay={0.1}>
            <div className="glass-strong flex h-full flex-col rounded-3xl p-6">
              <span className="mb-3 text-sm font-medium">Live spectrogram</span>
              <canvas ref={canvasRef} width={512} height={180} className="w-full flex-1 rounded-xl bg-secondary/40" />
              <span className="mt-3 text-xs text-muted-foreground">
                128-band mel · {TARGET_SR / 1000} kHz · 10s window, 5s hop
              </span>
            </div>
          </Reveal>
        </div>

        {/* Live layer breakdown */}
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

        {/* Alert history */}
        <Reveal delay={0.2}>
          <div className="glass-strong mt-6 rounded-3xl p-6">
            <span className="text-sm font-medium">Alert history</span>
            <div className="mt-4 max-h-64 space-y-2 overflow-y-auto">
              {alerts.length === 0 && (
                <p className="text-xs text-muted-foreground">No windows scored yet — stream a file or start the mic.</p>
              )}
              <AnimatePresence initial={false}>
                {alerts.map((a) => {
                  const m = VERDICT[a.level]
                  return (
                    <motion.div key={a.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                      className="flex items-center justify-between gap-3 rounded-xl bg-secondary/40 px-4 py-2 text-xs">
                      <span className="font-mono text-muted-foreground">{a.time}</span>
                      <span className="text-muted-foreground">call-{String(a.id).padStart(4, "0")}</span>
                      <span className="hidden text-muted-foreground sm:inline">fired: {a.layer}</span>
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-medium ${m.color} bg-current/10`}>
                        {a.level} · {a.risk}
                      </span>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </div>
        </Reveal>

        {error && <p className="mt-4 text-center font-mono text-xs text-threat">{error}</p>}
      </div>
    </section>
  )
}

function StatusDot({ status }: { status: "connecting" | "open" | "closed" }) {
  const c = status === "open" ? "bg-safe" : status === "connecting" ? "bg-cyan" : "bg-threat"
  return <span className={`h-2 w-2 rounded-full ${c} ${status !== "closed" ? "animate-pulse" : ""}`} />
}

function topLayer(b: Record<string, number>): string {
  let best = "", bv = -1
  for (const k of LAYERS) {
    const v = b[k] ?? 0
    if (v > bv) { bv = v; best = k }
  }
  return LAYER_LABELS[best] ?? best
}

/** Scrolling 128-band spectrogram from a live AnalyserNode. Returns a stop fn. */
function renderSpectrogram(canvas: HTMLCanvasElement | null, analyser: AnalyserNode | null): () => void {
  if (!canvas || !analyser) return () => {}
  const ctx = canvas.getContext("2d")
  if (!ctx) return () => {}
  const w = canvas.width, h = canvas.height
  ctx.clearRect(0, 0, w, h)
  const bins = analyser.frequencyBinCount
  const data = new Uint8Array(bins)
  let raf = 0, stopped = false
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
  return () => { stopped = true; cancelAnimationFrame(raf) }
}

/** Play decoded PCM aloud through an AnalyserNode and draw its spectrogram. Returns a stop fn. */
function playAndVisualize(pcm: Float32Array, canvas: HTMLCanvasElement | null): () => void {
  if (!canvas) return () => {}
  const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  const ac = new AC()
  const buffer = ac.createBuffer(1, pcm.length, TARGET_SR)
  buffer.copyToChannel(pcm, 0)
  const src = ac.createBufferSource()
  src.buffer = buffer
  const analyser = ac.createAnalyser()
  analyser.fftSize = 256
  src.connect(analyser)
  analyser.connect(ac.destination)
  src.start()
  const stopDraw = renderSpectrogram(canvas, analyser)
  const stop = () => { stopDraw(); try { src.stop() } catch {} ; ac.close().catch(() => {}) }
  src.onended = stop
  return stop
}
