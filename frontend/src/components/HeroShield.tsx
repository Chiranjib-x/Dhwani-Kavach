import { Canvas, useFrame } from "@react-three/fiber";
import { useRef, useEffect, useState, Suspense } from "react";
import * as THREE from "three";

function Shield() {
  const group = useRef<THREE.Group>(null!);
  const target = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      target.current.x = ny * 0.1;
      target.current.y = nx * 0.1;
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  useFrame((_, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * 0.12;
    group.current.rotation.x += (target.current.x - group.current.rotation.x) * 0.04;
    const yTarget = target.current.y;
    const cur = group.current.rotation.z;
    group.current.rotation.z += (yTarget - cur) * 0.04;
  });

  return (
    <group ref={group}>
      <mesh>
        <icosahedronGeometry args={[2.2, 1]} />
        <meshStandardMaterial color="#1A1D27" roughness={0.6} metalness={0.2} />
      </mesh>
      <mesh>
        <icosahedronGeometry args={[2.205, 1]} />
        <meshBasicMaterial color="#5EEAD4" wireframe transparent opacity={0.4} />
      </mesh>
    </group>
  );
}

export default function HeroShield() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return null;
  return (
    <Canvas
      className="!absolute inset-0"
      style={{ pointerEvents: "none" }}
      camera={{ position: [0, 0, 6], fov: 45 }}
      dpr={[1, 1.5]}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={0.6} color="#5EEAD4" />
      <Suspense fallback={null}>
        <Shield />
      </Suspense>
    </Canvas>
  );
}
