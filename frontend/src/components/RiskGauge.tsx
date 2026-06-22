import { useEffect, useRef, useState } from "react";

export default function RiskGauge({ target = 94 }: { target?: number }) {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!ref.current) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && !started.current) {
          started.current = true;
          const start = performance.now();
          const dur = 1600;
          const tick = (now: number) => {
            const t = Math.min(1, (now - start) / dur);
            const eased = 1 - Math.pow(1 - t, 3);
            setVal(Math.round(eased * target));
            if (t < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.4 }
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [target]);

  const R = 90;
  const CIRC = Math.PI * R; // half arc
  const pct = val / 100;
  const color = val > 70 ? "#FF4D6D" : val > 30 ? "#F59E0B" : "#22C55E";
  const verdict = val > 70 ? "CRITICAL" : val > 30 ? "REVIEW" : "PROTECTED";

  return (
    <div ref={ref} className="flex flex-col items-center justify-center">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <path
          d={`M 20 110 A ${R} ${R} 0 0 1 200 110`}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d={`M 20 110 A ${R} ${R} 0 0 1 200 110`}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRC}
          strokeDashoffset={CIRC * (1 - pct)}
          style={{ transition: "stroke 0.4s" }}
        />
      </svg>
      <div className="-mt-6 text-center">
        <div className="font-mono font-bold text-[56px] leading-none" style={{ color }}>{val}</div>
        <div className="mt-2 font-mono text-[11px] tracking-[0.2em]" style={{ color }}>
          {val} / 100 · {verdict}
        </div>
      </div>
    </div>
  );
}
