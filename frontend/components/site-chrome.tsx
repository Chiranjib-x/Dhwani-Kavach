"use client"

import { motion, useScroll } from "framer-motion"
import { ShieldCheck } from "lucide-react"

const links = [
  { href: "#threat", label: "Threat" },
  { href: "#layers", label: "Defense" },
  { href: "#dashboard", label: "Dashboard" },
  { href: "#simulate", label: "Simulate" },
]

export function SiteChrome() {
  const { scrollYProgress } = useScroll()
  return (
    <>
      <motion.div
        className="fixed left-0 right-0 top-0 z-50 h-0.5 origin-left bg-cyan"
        style={{ scaleX: scrollYProgress }}
      />  
      <header className="fixed inset-x-0 top-0 z-40 flex justify-center px-4 pt-4">
        <nav className="glass flex w-full max-w-3xl items-center justify-between rounded-full px-5 py-2.5">
          <a href="#" className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-5 w-5 text-cyan" />
            <span>Dhwani<span className="text-cyan">-Kavach</span></span>
          </a>
          <div className="hidden items-center gap-6 sm:flex">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-xs font-medium text-muted-foreground transition-colors hover:text-cyan"
              >
                {l.label}
              </a>
            ))}
          </div>
          <a
            href="#dashboard"
            className="rounded-full bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground"
          >
            Live demo
          </a>
        </nav>
      </header>
    </>
  )
}

export function SiteFooter() {
  return (
    <footer className="relative px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="glass-strong overflow-hidden rounded-3xl p-10 text-center sm:p-16">
          <h2 className="text-balance font-heading text-3xl font-semibold tracking-tight sm:text-5xl">
            Stop the voice you can&apos;t trust.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-pretty leading-relaxed text-muted-foreground">
            Deploy Dhwani-Kavach across your banking voice channels and neutralize deepfake fraud
            before it ever reaches an agent.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a
              href="#"
              className="rounded-full bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.03]"
            >
              Request a deployment
            </a>
            <a
              href="#"
              className="rounded-full glass px-7 py-3 text-sm font-medium transition-colors hover:text-cyan"
            >
              Read the whitepaper
            </a>
          </div>
        </div>
        <p className="mt-10 text-center text-xs text-muted-foreground">
          Dhwani-Kavach — AI voice fraud defense for banking security.
        </p>
      </div>
    </footer>
  )
}
