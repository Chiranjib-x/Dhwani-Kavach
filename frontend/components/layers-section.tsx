"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform, type MotionValue } from "framer-motion"
import { Fingerprint, AudioWaveform, Wind, Waves, Activity } from "lucide-react"

const layers = [
  {
    id: "AASIST",
    name: "AASIST",
    tag: "Spectro-temporal graph attention",
    desc: "A graph-attention network scans spectral and temporal artifacts left by every known synthesis engine — the deepfake's fingerprint.",
    icon: Fingerprint,
  },
  {
    id: "MFCC",
    name: "MFCC",
    tag: "Mel-frequency cepstral analysis",
    desc: "Cepstral coefficients map the true shape of a human vocal tract. Cloned voices smear these contours in ways the ear can't catch.",
    icon: AudioWaveform,
  },
  {
    id: "BREATH",
    name: "Breath Analysis",
    tag: "Respiration & micro-pause modeling",
    desc: "Real speakers breathe. We model inhalation cadence and micro-pauses that synthetic voices forget to reproduce.",
    icon: Wind,
  },
  {
    id: "PHASE",
    name: "Phase Coherence",
    tag: "Cross-band phase integrity",
    desc: "Genuine audio carries coherent phase across frequency bands. Vocoders and TTS engines break this coherence invisibly.",
    icon: Waves,
  },
  {
    id: "LIVENESS",
    name: "Liveness",
    tag: "Real-time presence challenge",
    desc: "Active liveness probes confirm a living human is speaking in the moment — defeating replay and pre-rendered clone attacks.",
    icon: Activity,
  },
]

export function LayersSection() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  })

  return (
    <section id="layers" ref={ref} className="relative w-full" style={{ height: `${layers.length * 80}vh` }}>
      <div className="sticky top-0 flex min-h-screen w-full flex-col items-center justify-center overflow-hidden px-6 pt-24">
        <div className="mb-10 text-center">
          <p className="mb-3 text-xs font-medium uppercase tracking-[0.25em] text-cyan">
            The defense
          </p>
          <h2 className="text-balance font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            Five detection layers, one verdict
          </h2>
        </div>

        <div className="relative h-[340px] w-full max-w-2xl">
          {layers.map((layer, i) => (
            <LayerCard
              key={layer.id}
              layer={layer}
              index={i}
              total={layers.length}
              progress={scrollYProgress}
            />
          ))}
        </div>

        {/* progress dots */}
        <div className="mt-10 flex items-center gap-3">
          {layers.map((l, i) => (
            <Dot key={l.id} index={i} total={layers.length} progress={scrollYProgress} />
          ))}
        </div>
      </div>
    </section>
  )
}

function LayerCard({
  layer,
  index,
  total,
  progress,
}: {
  layer: (typeof layers)[number]
  index: number
  total: number
  progress: MotionValue<number>
}) {
  const step = 1 / total
  const start = index * step
  const end = (index + 1) * step
  const margin = 0.05 // Controls the crossfade duration

  let input: number[]
  let op: number[]
  let yVal: number[]
  let scaleVal: number[]

  // Dynamically build the arrays so they are strictly increasing (Framer Motion requirement)
  if (index === 0) {
    input = [0, end - margin, end + margin]
    op = [1, 1, 0]
    yVal = [0, 0, -40]
    scaleVal = [1, 1, 0.92]
  } else if (index === total - 1) {
    input = [start - margin, start + margin, 1]
    op = [0, 1, 1]
    yVal = [40, 0, 0]
    scaleVal = [0.92, 1, 1]
  } else {
    input = [start - margin, start + margin, end - margin, end + margin]
    op = [0, 1, 1, 0]
    yVal = [40, 0, 0, -40]
    scaleVal = [0.92, 1, 1, 0.92]
  }

  const opacity = useTransform(progress, input, op)
  const y = useTransform(progress, input, yVal)
  const scale = useTransform(progress, input, scaleVal)
  const Icon = layer.icon

  return (
    <motion.div
      style={{ opacity, y, scale }}
      className="glass-strong absolute inset-0 flex flex-col justify-center rounded-3xl p-10"
    >
      <div className="flex items-center gap-4">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan/15 text-cyan">
          <Icon className="h-7 w-7" />
        </div>
        <div>
          <div className="font-mono text-xs text-muted-foreground">
            LAYER {index + 1} / {total}
          </div>
          <h3 className="font-heading text-2xl font-semibold sm:text-3xl">{layer.name}</h3>
        </div>
      </div>
      <p className="mt-5 text-sm font-medium uppercase tracking-wide text-cyan">{layer.tag}</p>
      <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">{layer.desc}</p>
    </motion.div>
  )
}

function Dot({
  index,
  total,
  progress,
}: {
  index: number
  total: number
  progress: MotionValue<number>
}) {
  const step = 1 / total
  const start = index * step
  const end = (index + 1) * step
  const margin = 0.05

  let input: number[]
  let widthVal: number[]
  let opVal: number[]

  if (index === 0) {
    input = [0, end - margin, end + margin]
    widthVal = [32, 32, 10]
    opVal = [1, 1, 0.3]
  } else if (index === total - 1) {
    input = [start - margin, start + margin, 1]
    widthVal = [10, 32, 32]
    opVal = [0.3, 1, 1]
  } else {
    input = [start - margin, start + margin, end - margin, end + margin]
    widthVal = [10, 32, 32, 10]
    opVal = [0.3, 1, 1, 0.3]
  }

  const width = useTransform(progress, input, widthVal)
  const opacity = useTransform(progress, input, opVal)

  return <motion.span style={{ width, opacity }} className="h-1.5 rounded-full bg-cyan" />
}