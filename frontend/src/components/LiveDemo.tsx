import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000";
type Phase = "idle" | "analyzing" | "done";
type Verdict = "PROTECTED" | "REVIEW" | "CRITICAL";

const LAYERS = ["AASIST", "Spectral Biometrics", "Breath Pattern", "Phase Coherence", "Active Liveness"];

function classify(name: string): { base: number; verdict: Verdict; range: [number, number] } {
  const n = name.toLowerCase();
  if (n.includes("real") || n.includes("human")) return { base: 8, verdict: "PROTECTED", range: [5, 15] };
  if (n.includes("elevenlabs") || n.includes("clone")) return { base: 94, verdict: "CRITICAL", range: [88, 99] };
  return { base: 67, verdict: "REVIEW", range: [55, 78] };
}

const verdictColor = (v: Verdict) => (v === "PROTECTED" ? "#22C55E" : v === "CRITICAL" ? "#FF4D6D" : "#F59E0B");

function formatSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(2)} MB`;
}

export default function LiveDemo() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [hover, setHover] = useState(false);
  const [result, setResult] = useState<{ score: number; verdict: Verdict; layers: number[] } | null>(null);

  async function handleFile(f: File | null) {
    if (!f) return;
  
    setFile(f);
    setPhase("analyzing");
  
    try {
      const form = new FormData();
      form.append("audio", f, f.name);
  
      const resp = await fetch(`${BACKEND}/api/analyze`, {
        method: "POST",
        body: form,
      });
  
      if (!resp.ok) {
        throw new Error(`Server error ${resp.status}`);
      }
  
      const data = await resp.json();
  
      let verdict: Verdict = "REVIEW";
  
      if (data.alert_level === "GREEN") {
        verdict = "PROTECTED";
      } else if (data.alert_level === "RED") {
        verdict = "CRITICAL";
      }
  
      setResult({
        score: data.risk_score,
        verdict,
        layers: [
          data.layer_breakdown.aasist || 0,
          data.layer_breakdown.mfcc || 0,
          data.layer_breakdown.breath || 0,
          data.layer_breakdown.phase || 0,
          data.layer_breakdown.liveness || 0,
        ],
      });
  
      setPhase("done");
    } catch (err) {
      console.error(err);
      setPhase("idle");
    }
  }
  
  function reset() {
    setFile(null);
    setResult(null);
    setPhase("idle");
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div
      className="mx-auto w-full max-w-[640px] rounded-2xl p-8 md:p-10"
      style={{ backgroundColor: "#0F1117", border: "1px solid rgba(255,255,255,0.07)" }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".wav,.mp3,.flac,.ogg,audio/*"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      <AnimatePresence mode="wait">
        {phase === "idle" && (
          <motion.button
            key="zone"
            type="button"
            onClick={() => inputRef.current?.click()}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            onDragOver={(e) => { e.preventDefault(); setHover(true); }}
            onDragLeave={() => setHover(false)}
            onDrop={(e) => { e.preventDefault(); setHover(false); handleFile(e.dataTransfer.files?.[0] ?? null); }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="w-full rounded-xl flex flex-col items-center justify-center text-center transition-colors"
            style={{
              padding: 48,
              border: `1.5px ${hover ? "solid" : "dashed"} ${hover ? "#5EEAD4" : "rgba(255,255,255,0.12)"}`,
              backgroundColor: hover ? "rgba(94,234,212,0.04)" : "transparent",
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#5EEAD4" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4M6 10l6-6 6 6" />
              <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
            </svg>
            <p className="mt-4 text-[15px] text-[#F1F5F9]">Drop audio here or click to browse</p>
            <p className="mt-1.5 font-mono text-[11px] text-[#64748B] tracking-wider">WAV · MP3 · FLAC · OGG</p>
          </motion.button>
        )}

        {phase === "analyzing" && file && (
          <motion.div
            key="analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="py-6"
          >
            <div className="flex items-center justify-between font-mono text-[12px] text-[#F1F5F9]">
              <span className="truncate pr-4">{file.name}</span>
              <span className="text-[#64748B]">{formatSize(file.size)}</span>
            </div>
            <div className="mt-6 h-[2px] w-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
              <motion.div
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 2.5, ease: "linear" }}
                style={{ backgroundColor: "#5EEAD4", height: "100%" }}
              />
            </div>
            <div className="mt-4 flex items-center gap-2 font-mono text-[11px] tracking-wider text-[#64748B]">
              <motion.span
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity }}
                className="inline-block w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: "#5EEAD4" }}
              />
              ANALYZING...
            </div>
          </motion.div>
        )}

        {phase === "done" && result && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-end justify-between">
              <div>
                <div className="font-mono text-[64px] leading-none font-bold" style={{ color: verdictColor(result.verdict) }}>
                  {String(result.score).padStart(2, "0")}
                </div>
                <div className="mt-2 font-mono text-[11px] tracking-[0.2em]" style={{ color: verdictColor(result.verdict) }}>
                  {result.verdict}
                </div>
              </div>
              <div className="font-mono text-[11px] text-[#64748B] text-right truncate max-w-[50%]">{file?.name}</div>
            </div>

            <div className="mt-8 space-y-3">
              {LAYERS.map((name, i) => (
                <motion.div
                  key={name}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1, duration: 0.4 }}
                  className="grid grid-cols-[140px_1fr_36px] items-center gap-4"
                >
                  <div className="text-[12px] text-[#F1F5F9]">{name}</div>
                  <div className="h-[2px] w-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${result.layers[i]}%` }}
                      transition={{ delay: i * 0.1 + 0.1, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                      style={{ height: "100%", backgroundColor: "#5EEAD4" }}
                    />
                  </div>
                  <div className="font-mono text-[11px] text-[#64748B] text-right">{result.layers[i]}</div>
                </motion.div>
              ))}
            </div>

            <button
              onClick={reset}
              className="mt-8 text-[12px] text-[#64748B] hover:text-[#5EEAD4] transition-colors"
            >
              ← Analyze another file
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
