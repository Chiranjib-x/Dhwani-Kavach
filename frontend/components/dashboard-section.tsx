"use client"

import { useRef } from "react"
import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion"
import { useEffect, useState } from "react"
import { Reveal } from "./reveal"

function useCountUp(target: number, active: boolean, duration = 2) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!active) return
    const controls = animate(0, target, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setVal(v),
    })
    return () => controls.stop()
  }, [active, target, duration])
  return val
}

const layerScores = [
  { name: "AASIST", score: 96 },
  { name: "MFCC", score: 91 },
  { name: "Breath", score: 88 },
  { name: "Phase", score: 94 },
  { name: "Liveness", score: 99 },
]

export function DashboardSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-120px" })
  const risk = useCountUp(94, inView, 2.4)

  // gauge
  const radius = 120
  const circumference = Math.PI * radius // half circle
  const dash = (risk / 100) * circumference

  return (
    <section id="dashboard" className="relative px-6 py-32">
      <div ref={ref} className="mx-auto max-w-6xl">
        <Reveal>
          <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.25em] text-cyan">
            Real-time intelligence
          </p>
          <h2 className="mx-auto max-w-3xl text-balance text-center font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            The threat dashboard, scoring as you watch
          </h2>
        </Reveal>

        <div className="mt-16 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          {/* Risk gauge */}
          <Reveal>
            <div className="glass-strong flex h-full flex-col items-center justify-center rounded-3xl p-10">
              <span className="mb-2 text-xs uppercase tracking-[0.25em] text-muted-foreground">
                Deepfake risk score
              </span>
              <div className="relative">
                <svg width="280" height="170" viewBox="0 0 280 170">
                  <path
                    d="M 20 150 A 120 120 0 0 1 260 150"
                    fill="none"
                    stroke="currentColor"
                    className="text-secondary"
                    strokeWidth="16"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 20 150 A 120 120 0 0 1 260 150"
                    fill="none"
                    stroke="currentColor"
                    className="text-threat"
                    strokeWidth="16"
                    strokeLinecap="round"
                    strokeDasharray={`${dash} ${circumference}`}
                  />
                </svg>
                <div className="absolute inset-x-0 bottom-2 flex flex-col items-center">
                  <span className="font-heading text-6xl font-semibold text-threat tabular-nums">
                    {Math.round(risk)}
                  </span>
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">
                    / 100 critical
                  </span>
                </div>
              </div>
              <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-threat/15 px-4 py-2 text-sm font-medium text-threat">
                <span className="h-2 w-2 animate-pulse rounded-full bg-threat" />
                Synthetic voice detected — transaction blocked
              </div>
            </div>
          </Reveal>

          {/* Layer breakdown bars */}
          <Reveal delay={0.15}>
            <div className="glass-strong flex h-full flex-col justify-center gap-5 rounded-3xl p-10">
              <span className="text-sm font-medium">Per-layer confidence</span>
              {layerScores.map((l, i) => (
                <LayerBar key={l.name} name={l.name} score={l.score} active={inView} delay={i * 0.12} />
              ))}
              <div className="mt-2 flex items-center justify-between border-t border-border pt-4 text-sm">
                <span className="text-muted-foreground">Verdict latency</span>
                <span className="font-mono text-safe">312&nbsp;ms</span>
              </div>
            </div>
          </Reveal>
        </div>

        {/* stat strip */}
        <Reveal delay={0.2}>
          <div className="mt-6 grid grid-cols-2 gap-6 md:grid-cols-4">
            {[
              { v: "99.2%", l: "Detection accuracy" },
              { v: "<400ms", l: "Verdict latency" },
              { v: "5", l: "Neural layers" },
              { v: "24/7", l: "Live monitoring" },
            ].map((s) => (
              <div key={s.l} className="glass rounded-2xl p-6 text-center">
                <div className="font-heading text-3xl font-semibold text-cyan">{s.v}</div>
                <div className="mt-1 text-xs text-muted-foreground">{s.l}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function LayerBar({
  name,
  score,
  active,
  delay,
}: {
  name: string
  score: number
  active: boolean
  delay: number
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 text-xs text-muted-foreground">{name}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
        <motion.div
          className="h-full rounded-full bg-cyan"
          initial={{ width: 0 }}
          animate={active ? { width: `${score}%` } : {}}
          transition={{ duration: 1.4, delay, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      <span className="w-9 shrink-0 text-right font-mono text-xs text-cyan">{score}</span>
    </div>
  )
}
