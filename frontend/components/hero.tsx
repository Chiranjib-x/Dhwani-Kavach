"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { ShieldCheck, ArrowDown } from "lucide-react"
import { useRef } from "react"

export function Hero() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  })
  const y = useTransform(scrollYProgress, [0, 1], [0, 160])
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0])

  return (
    <section
      ref={ref}
      className="relative flex min-h-screen flex-col items-center justify-center px-6 text-center"
    >
      <motion.div style={{ y, opacity }} className="relative z-10 flex flex-col items-center">
        {/* readability scrim behind hero copy */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[140%] w-[160%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            background:
              "radial-gradient(ellipse at center, color-mix(in oklch, var(--background) 78%, transparent) 0%, color-mix(in oklch, var(--background) 45%, transparent) 38%, transparent 70%)",
          }}
        />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="mb-8 inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-medium tracking-wide text-cyan"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-safe opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-safe" />
          </span>
          REAL-TIME DEEPFAKE VOICE DEFENSE
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="font-heading text-balance text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl md:text-8xl"
        >
          <span className="text-glow">Dhwani</span>
          <span className="text-cyan">-Kavach</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
          An AI voice-fraud shield for banking. Five neural detection layers expose cloned and
          synthetic voices in milliseconds, before a single transaction clears.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
        >
          <a
            href="#dashboard"
            className="group inline-flex items-center gap-2 rounded-full bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.03]"
          >
            <ShieldCheck className="h-4 w-4" />
            See it defend live
          </a>
          <a
            href="#threat"
            className="inline-flex items-center gap-2 rounded-full glass px-7 py-3 text-sm font-medium text-foreground transition-colors hover:text-cyan"
          >
            How attacks work
          </a>
        </motion.div>
      </motion.div>

      <motion.div
        style={{ opacity }}
        className="absolute bottom-10 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center gap-2 text-muted-foreground"
      >
        <span className="text-[10px] uppercase tracking-[0.25em]">Scroll</span>
        <motion.span
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        >
          <ArrowDown className="h-4 w-4 text-cyan" />
        </motion.span>
      </motion.div>

      {/* bottom fade into next section */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-background" />
    </section>
  )
}
