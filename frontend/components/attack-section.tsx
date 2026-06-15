"use client"

import { Reveal } from "./reveal"
import { motion } from "framer-motion"
import { Mic, Waypoints, ShieldAlert } from "lucide-react"

const steps = [
  {
    icon: Mic,
    title: "Capture",
    desc: "A caller's voice — real or cloned — enters the banking channel as raw audio.",
  },
  {
    icon: Waypoints,
    title: "Synthesize",
    desc: "Attackers use ElevenLabs-style cloning to forge a trusted customer's voiceprint.",
  },
  {
    icon: ShieldAlert,
    title: "Exploit",
    desc: "The deepfake authorizes a transfer. Human ears can't tell — but the network can.",
  },
]

export function AttackSection() {
  return (
    <section id="threat" className="relative px-6 py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.25em] text-threat">
            The threat
          </p>
          <h2 className="mx-auto max-w-3xl text-balance text-center font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            How a deepfake voice attack unfolds
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-center text-muted-foreground leading-relaxed">
            Synthetic speech now passes for human in under three seconds of audio. We trace every
            sample as it flows through the neural network, scoring authenticity frame by frame.
          </p>
        </Reveal>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.12}>
              <div className="glass relative h-full rounded-2xl p-7">
                <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-threat/15 text-threat">
                  <s.icon className="h-6 w-6" />
                </div>
                <div className="mb-1 font-mono text-xs text-muted-foreground">
                  0{i + 1}
                </div>
                <h3 className="mb-2 text-lg font-semibold">{s.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{s.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>

        {/* neural flow visualization */}
        <Reveal delay={0.2}>
          <div className="glass-strong mt-12 overflow-hidden rounded-2xl p-8">
            <div className="mb-6 flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">
                Voice data flowing through the network
              </span>
              <span className="font-mono text-xs text-cyan">live trace</span>
            </div>
            <NeuralFlow />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function NeuralFlow() {
  const layers = [4, 7, 9, 7, 3]
  const width = 920
  const height = 220
  const colW = width / (layers.length - 1)

  const nodes = layers.map((count, li) =>
    new Array(count).fill(0).map((_, ni) => ({
      x: li * colW,
      y: (height / (count + 1)) * (ni + 1),
    })),
  )

  const edges: { x1: number; y1: number; x2: number; y2: number; key: string }[] = []
  for (let li = 0; li < nodes.length - 1; li++) {
    nodes[li].forEach((a, ai) => {
      nodes[li + 1].forEach((b, bi) => {
        edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, key: `${li}-${ai}-${bi}` })
      })
    })
  }

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full min-w-[680px]">
        {edges.map((e, i) => (
          <motion.line
            key={e.key}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke="currentColor"
            className="text-cyan"
            strokeWidth={0.5}
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.18 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: (i % 30) * 0.01 }}
          />
        ))}
        {nodes.flatMap((col, li) =>
          col.map((n, ni) => (
            <motion.circle
              key={`${li}-${ni}`}
              cx={n.x}
              cy={n.y}
              r={4}
              className={li === nodes.length - 1 ? "text-safe" : "text-cyan"}
              fill="currentColor"
              initial={{ scale: 0, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: li * 0.15 + ni * 0.04, type: "spring" }}
            >
              <animate
                attributeName="opacity"
                values="1;0.4;1"
                dur={`${2 + (ni % 3)}s`}
                repeatCount="indefinite"
              />
            </motion.circle>
          )),
        )}
        {/* traveling signal */}
        {[0, 1, 2].map((k) => (
          <motion.circle key={k} r={3.5} className="text-safe" fill="currentColor">
            <animateMotion
              dur={`${3 + k}s`}
              repeatCount="indefinite"
              path={`M0,${110 + k * 10} L${width},${90 + k * 12}`}
            />
          </motion.circle>
        ))}
      </svg>
    </div>
  )
}
