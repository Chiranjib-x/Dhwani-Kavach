"use client"

import { useRef, useMemo, useState, useEffect } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { Float, Icosahedron } from "@react-three/drei"
import * as THREE from "three"

const CYAN = new THREE.Color("#34d6e6")
const SAFE = new THREE.Color("#3ee6a0")
const THREAT = new THREE.Color("#ff4d5e")

// Shared scroll progress (0..1) via a simple ref passed down
type SceneProps = { scrollRef: React.MutableRefObject<number> }

/* Holographic central shield */
function Shield({ scrollRef }: SceneProps) {
  const group = useRef<THREE.Group>(null)
  const inner = useRef<THREE.Mesh>(null)
  const wire = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const s = scrollRef.current
    if (group.current) {
      group.current.rotation.y = t * 0.15
      group.current.position.y = Math.sin(t * 0.6) * 0.12
      // subtle threat tint as user scrolls into attack sections
      const scale = 1 + Math.sin(t * 1.2) * 0.015
      group.current.scale.setScalar(scale * (1 - s * 0.12))
    }
    if (wire.current) {
      wire.current.rotation.y = -t * 0.25
      wire.current.rotation.x = t * 0.1
    }
    if (inner.current) {
      const mat = inner.current.material as THREE.MeshStandardMaterial
      // shift between safe-cyan and threat-red based on scroll band 0.15-0.45
      const threatBand = THREE.MathUtils.clamp((s - 0.15) / 0.25, 0, 1) * (1 - THREE.MathUtils.clamp((s - 0.55) / 0.2, 0, 1))
      const c = CYAN.clone().lerp(THREAT, threatBand * 0.6)
      mat.emissive.copy(c)
      mat.emissiveIntensity = 0.6 + Math.sin(t * 2) * 0.1
    }
  })

  return (
    <Float speed={1.4} rotationIntensity={0.25} floatIntensity={0.5}>
      <group ref={group}>
        {/* core crystalline shield */}
        <Icosahedron ref={inner} args={[1.25, 1]}>
          <meshStandardMaterial
            color="#0c2733"
            emissive={CYAN}
            emissiveIntensity={0.6}
            metalness={0.9}
            roughness={0.15}
            transparent
            opacity={0.85}
          />
        </Icosahedron>
        {/* wireframe overlay */}
        <Icosahedron ref={wire} args={[1.45, 1]}>
          <meshBasicMaterial color={CYAN} wireframe transparent opacity={0.35} />
        </Icosahedron>
        {/* outer halo shell */}
        <Icosahedron args={[1.7, 2]}>
          <meshBasicMaterial color={CYAN} wireframe transparent opacity={0.08} />
        </Icosahedron>
      </group>
    </Float>
  )
}

/* Rotating security rings */
function SecurityRings() {
  const g1 = useRef<THREE.Mesh>(null)
  const g2 = useRef<THREE.Mesh>(null)
  const g3 = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (g1.current) {
      g1.current.rotation.x = t * 0.3
      g1.current.rotation.y = t * 0.2
    }
    if (g2.current) {
      g2.current.rotation.y = -t * 0.35
      g2.current.rotation.z = t * 0.15
    }
    if (g3.current) {
      g3.current.rotation.x = -t * 0.2
      g3.current.rotation.z = -t * 0.25
    }
  })

  return (
    <group>
      <mesh ref={g1}>
        <torusGeometry args={[2.3, 0.012, 16, 120]} />
        <meshBasicMaterial color={CYAN} transparent opacity={0.6} />
      </mesh>
      <mesh ref={g2}>
        <torusGeometry args={[2.7, 0.008, 16, 120]} />
        <meshBasicMaterial color={SAFE} transparent opacity={0.45} />
      </mesh>
      <mesh ref={g3}>
        <torusGeometry args={[3.1, 0.006, 16, 120]} />
        <meshBasicMaterial color={CYAN} transparent opacity={0.3} />
      </mesh>
    </group>
  )
}

/* Voice waveforms orbiting the shield */
function VoiceWaves({ count = 3 }: { count?: number }) {
  const groups = useRef<THREE.Group[]>([])

  const rings = useMemo(() => {
    return new Array(count).fill(0).map((_, i) => {
      const radius = 2.0 + i * 0.45
      const bars = 90
      return { radius, bars, offset: i * 1.7, color: i % 2 === 0 ? CYAN : SAFE }
    })
  }, [count])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    groups.current.forEach((g, i) => {
      if (!g) return
      g.rotation.y = t * (0.12 + i * 0.05) + rings[i].offset
      g.rotation.x = Math.sin(t * 0.2 + i) * 0.25
      g.children.forEach((child, j) => {
        const mesh = child as THREE.Mesh
        const h = 0.08 + Math.abs(Math.sin(t * 3 + j * 0.4 + i)) * 0.5
        mesh.scale.y = h
      })
    })
  })

  return (
    <group>
      {rings.map((ring, i) => (
        <group key={i} ref={(el) => { if (el) groups.current[i] = el }}>
          {new Array(ring.bars).fill(0).map((_, j) => {
            const angle = (j / ring.bars) * Math.PI * 2
            return (
              <mesh
                key={j}
                position={[Math.cos(angle) * ring.radius, 0, Math.sin(angle) * ring.radius]}
                rotation={[0, -angle, 0]}
              >
                <boxGeometry args={[0.02, 0.4, 0.02]} />
                <meshBasicMaterial color={ring.color} transparent opacity={0.7} />
              </mesh>
            )
          })}
        </group>
      ))}
    </group>
  )
}

/* AI neural network particles in 3D space */
function NeuralField({ count = 900 }: { count?: number }) {
  const points = useRef<THREE.Points>(null)

  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const speeds = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      const r = 4 + Math.random() * 6
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = (Math.random() - 0.5) * 9
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta)
      speeds[i] = 0.2 + Math.random() * 0.8
    }
    return { positions, speeds }
  }, [count])

  useFrame((state) => {
    if (!points.current) return
    const t = state.clock.elapsedTime
    points.current.rotation.y = t * 0.04
    const arr = points.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      arr[i * 3 + 1] += Math.sin(t * speeds[i] + i) * 0.002
    }
    points.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        color={CYAN}
        transparent
        opacity={0.7}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

/* Threat pulses traveling outward */
function ThreatPulses({ scrollRef }: SceneProps) {
  const pulses = useRef<THREE.Mesh[]>([])
  const data = useMemo(
    () =>
      new Array(6).fill(0).map((_, i) => ({
        angle: (i / 6) * Math.PI * 2,
        offset: i * 0.6,
        threat: i % 2 === 0,
      })),
    [],
  )

  useFrame((state) => {
    const t = state.clock.elapsedTime
    pulses.current.forEach((m, i) => {
      if (!m) return
      const phase = ((t * 0.5 + data[i].offset) % 3) / 3
      const dist = phase * 4.5
      m.position.x = Math.cos(data[i].angle) * dist
      m.position.z = Math.sin(data[i].angle) * dist
      m.position.y = Math.sin(t + i) * 0.3
      const mat = m.material as THREE.MeshBasicMaterial
      mat.opacity = (1 - phase) * 0.9
      const scale = 0.06 + phase * 0.12
      m.scale.setScalar(scale)
    })
  })

  return (
    <group>
      {data.map((d, i) => (
        <mesh key={i} ref={(el) => { if (el) pulses.current[i] = el }}>
          <sphereGeometry args={[1, 12, 12]} />
          <meshBasicMaterial
            color={d.threat ? THREAT : SAFE}
            transparent
            opacity={0.8}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  )
}

/* Mouse + scroll reactive camera rig */
function CameraRig({ scrollRef, mouse }: SceneProps & { mouse: React.MutableRefObject<{ x: number; y: number }> }) {
  const { camera } = useThree()
  useFrame(() => {
    const s = scrollRef.current
    const targetX = mouse.current.x * 1.6
    const targetY = 0.4 + mouse.current.y * 1.0 + s * 0.6
    const targetZ = 7.5 - s * 1.2
    camera.position.x += (targetX - camera.position.x) * 0.04
    camera.position.y += (targetY - camera.position.y) * 0.04
    camera.position.z += (targetZ - camera.position.z) * 0.04
    camera.lookAt(0, 0, 0)
  })
  return null
}

export function Scene3D() {
  const scrollRef = useRef(0)
  const mouse = useRef({ x: 0, y: 0 })
  const wrapRef = useRef<HTMLDivElement>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setReady(true)
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      scrollRef.current = max > 0 ? window.scrollY / max : 0
      // fade the 3D backdrop after the hero so content panels stay readable
      if (wrapRef.current) {
        const vh = window.innerHeight
        const fade = THREE.MathUtils.clamp(1 - (window.scrollY - vh * 0.4) / (vh * 0.6), 0.28, 1)
        wrapRef.current.style.opacity = String(fade)
      }
    }
    const onMove = (e: PointerEvent) => {
      mouse.current.x = (e.clientX / window.innerWidth) * 2 - 1
      mouse.current.y = -((e.clientY / window.innerHeight) * 2 - 1)
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    window.addEventListener("pointermove", onMove, { passive: true })
    onScroll()
    return () => {
      window.removeEventListener("scroll", onScroll)
      window.removeEventListener("pointermove", onMove)
    }
  }, [])

  return (
    <div ref={wrapRef} className="fixed inset-0 h-screen w-full transition-opacity duration-200" aria-hidden="true">
      {ready && (
        <Canvas
          camera={{ position: [0, 0.4, 7.5], fov: 50 }}
          dpr={[1, 1.75]}
          gl={{ antialias: true, alpha: true }}
        >
          <color attach="background" args={["#0a1018"]} />
          <fog attach="fog" args={["#0a1018", 8, 18]} />
          <ambientLight intensity={0.5} />
          <pointLight position={[5, 5, 5]} intensity={2.2} color={"#34d6e6"} />
          <pointLight position={[-5, -3, 2]} intensity={1.4} color={"#3ee6a0"} />
          <pointLight position={[0, 0, 4]} intensity={1.0} color={"#ffffff"} />

          <Shield scrollRef={scrollRef} />
          <SecurityRings />
          <VoiceWaves count={3} />
          <NeuralField count={900} />
          <ThreatPulses scrollRef={scrollRef} />
          <CameraRig scrollRef={scrollRef} mouse={mouse} />
        </Canvas>
      )}
    </div>
  )
}
