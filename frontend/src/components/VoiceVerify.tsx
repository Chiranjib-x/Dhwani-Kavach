import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// The real v2 flow: enroll a voice once, then verify identity with a random
// one-time digit challenge run through the cascade (quality -> voice match ->
// phrase -> liveness). Retrain ("reenroll") re-runs that same verification
// against your enrolled voice and captures the accepted clips as a fresh
// voiceprint. Talks to /v2/*.
const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000";

const C = {
  cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8",
  text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", faint: "rgba(255,255,255,0.08)", bg: "#08090C",
};

type Mode = "verify" | "enroll" | "reenroll";
type Scores = {
  quality?: { ok: boolean; snr_db: number; speech_sec: number } | null;
  content?: { heard: string; edits: number; ok: boolean } | null;
  liveness?: { bonafide_p: number; pop_p?: number; ok: boolean } | null;
  speaker?: { cosine: number; ok: boolean } | null;
};
type Verdict = {
  verdict: string; gate_failed: string | null; reasons: string[]; scores: Scores;
  attempts_left?: number; new_challenge?: string; redo_slot?: number | null;
  slots_done?: number; slots_total?: number;
};

const MIME = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]
  .find((m) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(m));

const MIC_ERRORS: Record<string, string> = {
  NotAllowedError: "Microphone access is blocked. Click the lock icon in the address bar → allow the microphone, then reload.",
  NotFoundError: "No microphone found. Plug one in or check system sound settings, then press Start.",
  NotReadableError: "Your microphone is in use or not responding. Close apps using the mic (Zoom, Meet, Teams) or pick another mic, then Start.",
  SecurityError: "This page needs a secure (https) link — open the https URL.",
};
const REASON_COPY: Record<string, string> = {
  NO_AUDIO: "We didn't get any audio — press Start and speak.",
  TOO_SHORT: "That was too short — read the whole code.",
  TOO_LONG: "That was too long — just read the digits and stop.",
  TOO_QUIET: "You're too quiet — move the mic closer and speak up.",
  CLIPPING: "The mic is overloading — move it a little further from your mouth.",
  NOISY: "Too much background noise — move somewhere quieter and retry.",
  NO_SPEECH: "We didn't catch enough speech — press Start and read the whole code.",
  WRONG_PHRASE: "That didn't match the code — read the new digits shown above.",
  SPOOF_SUSPECTED: "This didn't sound like a live human voice.",
  VOICE_MISMATCH: "This voice doesn't match the enrolled customer.",
  VOICE_UNVERIFIED: "We couldn't confirm this is your enrolled voice — read the new code again.",
  BORDERLINE_VOICE: "We couldn't be sure — sending you to an extra check.",
  SESSION_EXPIRED: "That took too long — starting a fresh code.",
  SESSION_USED: "That session is already finished — starting fresh.",
  TOO_MANY_ATTEMPTS: "Too many tries — starting over.",
  NOT_ENROLLED: "This id isn't enrolled yet — switch to Enroll first.",
  ALREADY_ENROLLED: "This id is already enrolled.",
  ENROLL_INCONSISTENT: "Those clips didn't sound like the same voice — please re-record.",
  LOCKED: "Too many failed attempts — try again in 15 minutes or contact the bank.",
  BAD_AUDIO_FORMAT: "We couldn't read that recording — please retry.",
  BAD_REQUEST: "Something went wrong — please retry.",
};

const verdictColor = (v: string) =>
  ["ACCEPT", "ENROLLED", "REENROLLED", "ENROLL_SLOT_OK"].includes(v) ? C.ok
  : ["REJECT", "LOCKED"].includes(v) ? C.threat : C.warn;

const MODE_LABEL: Record<Mode, string> = { verify: "Verify", enroll: "Enroll", reenroll: "Retrain" };
const isEnrollLike = (m: Mode) => m === "enroll" || m === "reenroll";  // multi-slot capture
const showsChallenge = (m: Mode) => m === "verify" || m === "reenroll"; // reads a one-time code

const GATES: { key: keyof Scores; n: string; label: string; fmt: (s: any) => string }[] = [
  { key: "speaker", n: "01", label: "Voice match", fmt: (s) => `match ${s.cosine}` },
  { key: "content", n: "02", label: "Phrase", fmt: (s) => `heard ${s.heard || "—"}` },
  { key: "liveness", n: "03", label: "Liveness", fmt: (s) => `live ${Math.round((s.bonafide_p || 0) * 100)}%${s.pop_p != null ? ` · pop ${s.pop_p}` : ""}` },
  { key: "quality", n: "04", label: "Quality", fmt: (s) => `${s.snr_db} dB · ${s.speech_sec}s` },
];

export default function VoiceVerify() {
  const [mode, setMode] = useState<Mode>("verify");
  const [userId, setUserId] = useState("");
  const [fixedCode, setFixedCode] = useState(false);   // testing: disable random challenge
  const [fixedPrime, setFixedPrime] = useState(false);  // testing: disable random plosive word
  const [ready, setReady] = useState(false);
  const [banner, setBanner] = useState<{ msg: string; kind: "error" | "info" } | null>(null);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [prime, setPrime] = useState<string | null>(null);   // plosive word for pop-noise liveness
  const [prompts, setPrompts] = useState<string[]>([]);
  const [slot, setSlot] = useState(0);
  const [slotsTotal, setSlotsTotal] = useState(0);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [level, setLevel] = useState(0);
  const [muted, setMuted] = useState(false);
  const [result, setResult] = useState<Verdict | null>(null);

  const session = useRef<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const acRef = useRef<AudioContext | null>(null);
  const raf = useRef<number>(0);

  // health gate — enable the button once models are warm
  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const h = await (await fetch(`${BACKEND}/v2/health`)).json();
        if (h.models_loaded) { setReady(true); return; }
      } catch { /* backend not up yet */ }
      if (!stop) setTimeout(poll, 3000);
    };
    poll();
    return () => { stop = true; };
  }, []);

  const reset = (m: Mode) => {
    setMode(m); session.current = null; setChallenge(null); setPrime(null); setPrompts([]);
    setSlot(0); setSlotsTotal(0); setResult(null); setBanner(null);
  };

  async function startSession(): Promise<any | null> {
    if (!userId.trim()) { setBanner({ msg: "Enter an account / user id first.", kind: "error" }); return null; }
    const r = await (await fetch(`${BACKEND}/v2/session`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId.trim(), mode, randomize: !fixedCode, randomize_prime: !fixedPrime }),
    })).json();
    if (r.error) { setBanner({ msg: REASON_COPY[r.error] || r.error, kind: "error" }); return null; }
    session.current = r.session_id;
    if (r.challenge) setChallenge(r.challenge);
    setPrime(r.prime || null);
    if (r.prompts) setPrompts(r.prompts);
    setSlotsTotal(r.slots_total || (r.prompts?.length ?? 0));
    return r;
  }

  const startMeter = (stream: MediaStream) => {
    const AC = window.AudioContext ?? (window as any).webkitAudioContext;
    const ac = new AC(); acRef.current = ac;
    const an = ac.createAnalyser(); an.fftSize = 2048;
    ac.createMediaStreamSource(stream).connect(an);
    const buf = new Float32Array(an.fftSize); let silentSince = performance.now();
    const tick = () => {
      an.getFloatTimeDomainData(buf);
      let s = 0; for (const v of buf) s += v * v;
      const rms = Math.sqrt(s / buf.length);
      setLevel(Math.min(100, rms * 800));
      if (rms > 0.001) silentSince = performance.now();
      setMuted(performance.now() - silentSince >= 1500);
      raf.current = requestAnimationFrame(tick);
    };
    tick();
  };

  const record = useCallback(async (maxMs = 9000): Promise<Blob | null> => {
    let stream: MediaStream;
    try {
      // RAW capture: echo-cancellation / noise-suppression / AGC all OFF. Those
      // filters strip the low-frequency breath "pop noise" that near-field
      // liveness relies on to catch a clone played through a speaker.
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
    } catch (e: any) {
      if (e.name === "OverconstrainedError") stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      else { setBanner({ msg: MIC_ERRORS[e.name] || `Mic error: ${e.name}`, kind: "error" }); return null; }
    }
    stream.getTracks()[0].onended = () => setBanner({ msg: "Microphone disconnected — please retry.", kind: "error" });
    startMeter(stream);
    setRecording(true);
    return new Promise((res) => {
      chunks.current = [];
      const mr = new MediaRecorder(stream, MIME ? { mimeType: MIME } : undefined);
      rec.current = mr;
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = () => {
        cancelAnimationFrame(raf.current); acRef.current?.close();
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false); setLevel(0); setMuted(false);
        res(new Blob(chunks.current, { type: mr.mimeType }));
      };
      mr.start();
      setTimeout(() => mr.state === "recording" && mr.stop(), maxMs);
    });
  }, []);

  const stopRec = () => rec.current?.state === "recording" && rec.current.stop();

  async function submit(blob: Blob, s: number): Promise<Verdict | null> {
    const fd = new FormData();
    fd.append("session_id", session.current!); fd.append("slot", String(s));
    fd.append("file", blob, `clip.${blob.type.includes("mp4") ? "mp4" : "webm"}`);
    const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 30000);
    try {
      const r = await fetch(`${BACKEND}/v2/audio`, { method: "POST", body: fd, signal: ctl.signal });
      return await r.json();
    } catch {
      setBanner({ msg: "Upload failed — check your connection and retry. Your recording was not counted.", kind: "error" });
      return null;
    } finally { clearTimeout(to); }
  }

  async function run() {
    setBusy(true); setBanner(null); setResult(null);
    try {
      if (!session.current) {
        const s = await startSession();
        if (!s) return;
        if (isEnrollLike(mode)) setSlot(0);
      }
      const blob = await record();
      if (!blob) return;
      setBanner({ msg: "Checking…", kind: "info" });
      const curSlot = isEnrollLike(mode) ? slot : 0;
      const v = await submit(blob, curSlot);
      if (!v) return;
      setBanner(null); setResult(v);

      if (mode === "verify") {
        if (v.verdict === "RETRY") {
          if (v.new_challenge) setChallenge(v.new_challenge); else session.current = null;
        } else session.current = null;
      } else if (mode === "enroll") {
        if (v.verdict === "ENROLL_SLOT_OK") setSlot(v.slots_done ?? slot + 1);
        else if (v.verdict === "ENROLLED") {
          setBanner({ msg: "Enrolled. You can Verify now.", kind: "info" });
          session.current = null;
        }
        else if (v.verdict === "RETRY" && v.redo_slot != null) setSlot(v.redo_slot);
      } else {  // reenroll — reads a fresh code per clip, each verified against the enrolled voice
        if (v.verdict === "ENROLL_SLOT_OK") {
          setSlot(v.slots_done ?? slot + 1);
          if (v.new_challenge) setChallenge(v.new_challenge);
        }
        else if (v.verdict === "REENROLLED") {
          setBanner({ msg: "Voiceprint retrained. You can Verify with the updated voice.", kind: "info" });
          session.current = null;
        }
        else if (v.verdict === "RETRY") {
          if (v.new_challenge) setChallenge(v.new_challenge);   // code rotates on every re-record
          if (v.redo_slot != null) setSlot(v.redo_slot);
        }
        else session.current = null;   // REJECT / LOCKED -> start over
      }
    } finally { setBusy(false); }
  }

  const scores = result?.scores;
  const detail = (result?.reasons || []).map((c) => REASON_COPY[c] || c).join("  ");

  return (
    <div className="rounded-2xl p-6 md:p-8" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
      {!ready && (
        <div className="mb-4 rounded-lg px-4 py-3 text-[13px]" style={{ background: "rgba(56,189,248,0.08)", border: `1px solid ${C.info}`, color: "#bcd2ff" }}>
          Waking up the engine… this can take up to a minute on first load.
        </div>
      )}

      {/* id + mode tabs */}
      <label className="text-[12px]" style={{ color: C.muted }}>Account / user id</label>
      <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="e.g. chris" autoComplete="off"
        className="w-full mt-1.5 px-3 py-2.5 rounded-lg text-[15px] outline-none"
        style={{ background: C.bg, border: `1px solid ${C.faint}`, color: C.text }} />

      <div className="flex gap-2 mt-4">
        {(["verify", "enroll", "reenroll"] as Mode[]).map((m) => (
          <button key={m} onClick={() => reset(m)} disabled={recording || busy}
            className="flex-1 py-2.5 rounded-lg text-[14px] font-semibold transition-colors"
            style={mode === m
              ? { background: C.cyan, color: C.bg, border: `1px solid ${C.cyan}` }
              : { background: C.bg, color: C.muted, border: `1px solid ${C.faint}` }}>
            {MODE_LABEL[m]}
          </button>
        ))}
      </div>
      {mode === "reenroll" && (
        <p className="mt-2 text-[12px]" style={{ color: C.muted }}>
          Updates your voiceprint (voice changed, poor original enrollment, ...). You read a fresh
          code for each clip; every clip must match your enrolled voice to be saved.
        </p>
      )}

      {/* testing toggles: fixed code + fixed word */}
      {mode === "verify" && (
        <div className="mt-3 space-y-2">
          <label className="flex items-center gap-2 text-[12px] cursor-pointer" style={{ color: C.muted }}>
            <input type="checkbox" checked={fixedCode} disabled={recording || busy}
              onChange={(e) => { setFixedCode(e.target.checked); session.current = null; setChallenge(null); }} />
            Fixed code <span className="font-mono">123456</span>
          </label>
          <label className="flex items-center gap-2 text-[12px] cursor-pointer" style={{ color: C.muted }}>
            <input type="checkbox" checked={fixedPrime} disabled={recording || busy}
              onChange={(e) => { setFixedPrime(e.target.checked); session.current = null; setPrime(null); }} />
            Fixed word <span className="font-mono">papa</span>
          </label>
          <p className="text-[11px]" style={{ color: C.muted }}>Testing only — disables replay protection</p>
        </div>
      )}

      {/* prompt / challenge */}
      {showsChallenge(mode) && challenge && (
        <div className="mt-5">
          <div className="text-[12px]" style={{ color: C.muted }}>
            {mode === "reenroll" && slotsTotal ? `Clip ${slot + 1} of ${slotsTotal} — ` : ""}
            Hold the phone <b style={{ color: C.text }}>close to your mouth</b> and say{prime ? " the word, then" : ""} the digits:
          </div>
          <div className="mt-1.5 py-3 rounded-xl text-center font-bold"
            style={{ background: C.bg, letterSpacing: "0.3em", fontSize: 34, color: C.text }}>
            {prime && <span style={{ color: C.cyan, letterSpacing: "0.05em" }}>{prime.toUpperCase()}&nbsp;&nbsp;</span>}
            {challenge.split("").join(" ")}
          </div>
        </div>
      )}
      {mode === "enroll" && prompts[slot] && (
        <div className="mt-5">
          <div className="text-[12px]" style={{ color: C.muted }}>Clip {slot + 1} of {prompts.length} — read this aloud:</div>
          <div className="mt-1.5 p-3 rounded-xl text-[15px]" style={{ background: C.bg, color: C.text }}>{prompts[slot]}</div>
        </div>
      )}

      {/* muted warning + level meter */}
      {muted && (
        <div className="mt-4 rounded-lg px-4 py-2.5 text-[13px]" style={{ background: "rgba(255,77,109,0.1)", border: `1px solid ${C.threat}`, color: "#ffb4b4" }}>
          We can't hear you — is your microphone muted?
        </div>
      )}
      <div className="mt-4 h-2.5 rounded-full overflow-hidden" style={{ background: C.bg }}>
        <div style={{ height: "100%", width: `${level}%`, background: `linear-gradient(90deg,${C.ok},${C.warn})`, transition: "width .05s" }} />
      </div>

      {/* action button */}
      {recording ? (
        <button onClick={stopRec} className="w-full mt-4 py-3.5 rounded-xl text-[16px] font-bold"
          style={{ background: C.bg, color: C.text, border: `1px solid ${C.faint}` }}>Stop</button>
      ) : (
        <button onClick={run} disabled={!ready || busy}
          className="w-full mt-4 py-3.5 rounded-xl text-[16px] font-bold transition-opacity"
          style={{ background: C.cyan, color: C.bg, opacity: !ready || busy ? 0.5 : 1 }}>
          {busy ? "Working…" : mode === "enroll" ? "Start enrollment" : mode === "reenroll" ? "Start retraining" : "Start verification"}
        </button>
      )}

      {banner && (
        <div className="mt-3 rounded-lg px-4 py-2.5 text-[13px]"
          style={banner.kind === "error"
            ? { background: "rgba(255,77,109,0.1)", border: `1px solid ${C.threat}`, color: "#ffb4b4" }
            : { background: "rgba(56,189,248,0.08)", border: `1px solid ${C.info}`, color: "#bcd2ff" }}>
          {banner.msg}
        </div>
      )}

      {/* gate cards */}
      {scores && (
        <div className="grid grid-cols-2 gap-2.5 mt-5">
          {GATES.map((g) => {
            const s = scores[g.key] as any;
            const col = s ? (s.ok ? C.ok : C.threat) : C.faint;
            return (
              <div key={g.key} className="rounded-lg p-3" style={{ background: C.bg, border: `1px solid ${s ? col : C.faint}` }}>
                <div className="font-mono text-[11px]" style={{ color: C.muted }}>{g.n} · {g.label}</div>
                <div className="mt-1 text-[13px] font-semibold" style={{ color: s ? col : C.muted }}>
                  {s ? g.fmt(s) : "—"}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* verdict */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="mt-5 rounded-xl py-4 text-center font-extrabold text-[22px]"
            style={{ color: verdictColor(result.verdict), background: C.bg, border: `1px solid ${verdictColor(result.verdict)}` }}>
            {result.verdict.replace(/_/g, " ")}
            {result.attempts_left != null && result.verdict === "RETRY" && (
              <span className="block text-[12px] font-normal mt-1" style={{ color: C.muted }}>{result.attempts_left} attempts left</span>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      {detail && <div className="mt-2 text-[12px]" style={{ color: C.muted }}>{detail}</div>}
    </div>
  );
}
