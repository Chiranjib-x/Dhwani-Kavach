import dynamic from "next/dynamic"
import { Hero } from "@/components/hero"
import { AttackSection } from "@/components/attack-section"
import { LayersSection } from "@/components/layers-section"
import { DashboardSection } from "@/components/dashboard-section"
import { SimulationSection } from "@/components/simulation-section"
import { SiteChrome, SiteFooter } from "@/components/site-chrome"

const Scene3D = dynamic(() => import("@/components/scene-3d").then((m) => m.Scene3D))

export default function Page() {
  return (
    // Changed overflow-x-hidden to overflow-x-clip right here
    <main className="relative min-h-screen overflow-x-clip bg-background">
      {/* animated aurora + grid backdrop */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="aurora" />
        <div className="absolute inset-0 grid-fade" />
      </div>

      {/* 3D layer */}
      <Scene3D />

      {/* foreground content */}
      <div className="relative z-10">
        <SiteChrome />
        <Hero />
        <AttackSection />g
        <LayersSection />
        <DashboardSection />
        <SimulationSection />
        <SiteFooter />
      </div>
    </main>
  )
}