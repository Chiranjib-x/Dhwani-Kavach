import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useRef, useState } from "react"

// Voice fingerprinting (1:1 voiceprint) demo — the identity tier the shield's
// escalation hands off to. Talks to the standalone verify_app (/v2/*): enroll a
// speaker once by reading three prompts, then verify by reading a fresh one-time
// code. The ECAPA speaker embedding proves it's THIS person (not just "a live
// human"), on top of the content + liveness gates.
//
// verify_app runs as its own server. Point VITE_VERIFY_API_URL at it (default
// :8001, since the shield owns :8000). The configured URL is shown on the page.

export const Route = createFileRoute("/voiceprint")({ component: Voiceprint })

const VERIFY_API = import.meta.env.VITE_VERIFY_API_URL || "http://localhost:8001"
const ENROLL_MS = 8000
const VERIFY_MS = 6000

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", faint: "rgba(255,255,255,0.08)" }

type Scores = {
  quality?: { snr_db?: number; speech_sec?: number } | null
  content?: { edits?: number; ok?: boolean } | null
  liveness?: { bonafide_p?: number } | null
  speaker?: { cosine?: number; ok?: boolean } | null
}
type Verdict = {
  verdict: string; gate_failed?: string | null; reasons?: string[]; scores?: Scores
  attempts_left?: number; new_challenge?: string; slots_done?: number; slots_total?: number
  error?: string
}

async function postJSON(path: string, body: unknown) {
  const r = await fetch(`${VERIFY_API}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  })
  return r.json()
}

async function postAudio(session_id: string, slot: number, blob: Blob): Promise<Verdict> {
  const fd = new FormData()
  fd.append("session_id", session_id)
  fd.append("slot", String(slot))
  fd.append("file", blob, "clip.webm")
  const r = await fetch(`${VERIFY_API}/v2/audio`, { method: "POST", body: fd })
  return r.json()
}

// Record one clip for `ms`, ticking the countdown. Resolves with the audio Blob.
async function recordClip(ms: number, onTick: (s: number) => void): Promise<Blob> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const rec = new MediaRecorder(stream)
  const chunks: Blob[] = []
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data)
  return new Promise<Blob>((resolve, reject) => {
    rec.onstop = () => { stream.getTracks().forEach((t) => t.stop()); resolve(new Blob(chunks, { type: rec.mimeType })) }
    rec.onerror = (e) => reject(e)
    rec.start()
    let left = Math.ceil(ms / 1000); onTick(left)
    const iv = setInterval(() => { left -= 1; onTick(left); if (left <= 0) clearInterval(iv) }, 1000)
    setTimeout(() => rec.state !== "inactive" && rec.stop(), ms)
  })
}

function Voiceprint() {
  const [userId, setUserId] = useState("demo-user")
  const [mode, setMode] = useState<"enroll" | "verify">("verify")
  const [busy, setBusy] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState<string | null>(null)
  // enroll state
  const [prompts, setPrompts] = useState<string[]>([])
  const [slot, setSlot] = useState(0)
  const [enrollMsg, setEnrollMsg] = useState<string | null>(null)
  // verify state
  const [challenge, setChallenge] = useState<string | null>(null)
  const [result, setResult] = useState<Verdict | null>(null)
  const sessionRef = useRef<string | null>(null)

  const reset = () => {
    setError(null); setResult(null); setPrompts([]); setSlot(0)
    setChallenge(null); setEnrollMsg(null); sessionRef.current = null
  }

  // --- ENROLL ------------------------------------------------------------- //
  const startEnroll = useCallback(async () => {
    reset(); setBusy(true)
    try {
      const s = await postJSON("/v2/session", { user_id: userId.trim(), mode: "enroll" })
      if (s.error) { setError(s.error === "ALREADY_ENROLLED" ? "Already enrolled — switch to Verify, or reset first." : s.error); return }
      sessionRef.current = s.session_id
      setPrompts(s.prompts || [])
      setSlot(0)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }, [userId])

  const recordEnrollSlot = useCallback(async () => {
    if (!sessionRef.current) return
    setBusy(true); setError(null); setEnrollMsg(null)
    try {
      const blob = await recordClip(ENROLL_MS, setCountdown)
      const v = await postAudio(sessionRef.current, slot, blob)
      if (v.verdict === "ENROLLED") { setEnrollMsg("✓ Enrolled — voiceprint stored. Switch to Verify to test it."); setPrompts([]) }
      else if (v.verdict === "ENROLL_SLOT_OK") { setEnrollMsg(`Slot ${slot + 1} captured (${v.slots_done}/${v.slots_total}).`); setSlot((v.slots_done ?? slot + 1)) }
      else { setEnrollMsg(`Retry slot ${slot + 1}: ${(v.reasons || [v.gate_failed]).join(", ")}`) }
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false); setCountdown(0) }
  }, [slot])

  // --- VERIFY ------------------------------------------------------------- //
  const startVerify = useCallback(async () => {
    reset(); setBusy(true)
    try {
      const s = await postJSON("/v2/session", { user_id: userId.trim(), mode: "verify" })
      if (s.error) { setError(s.error === "NOT_ENROLLED" ? "Not enrolled yet — run Enroll first." : s.error); return }
      sessionRef.current = s.session_id
      setChallenge(s.challenge)
      const blob = await recordClip(VERIFY_MS, setCountdown)
      const v = await postAudio(s.session_id, 0, blob)
      setResult(v)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false); setCountdown(0) }
  }, [userId])

  const verdictColor = (v?: string) => v === "ACCEPT" ? C.ok : v === "STEP_UP" ? C.warn : C.threat
  const cosine = result?.scores?.speaker?.cosine

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8 px-6 py-16" style={{ backgroundColor: "#0A0B0F", color: C.text }}>
      <div className="text-center max-w-xl">
        <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · VOICEPRINT</div>
        <h1 className="mt-3 text-3xl font-semibold">One-to-one voice fingerprinting</h1>
        <p className="mt-2 text-sm" style={{ color: C.muted }}>
          Enroll once by reading three lines. Then verify by reading a fresh one-time code — an
          ECAPA speaker embedding confirms it's <em>you</em>, not just a live human. This is the
          identity tier the shield's step-up hands off to.
        </p>
      </div>

      {/* mode + user */}
      <div className="w-full max-w-xl flex flex-wrap items-center gap-3">
        <div className="flex rounded-full overflow-hidden" style={{ border: `1px solid ${C.faint}` }}>
          {(["verify", "enroll"] as const).map((m) => (
            <button key={m} onClick={() => { setMode(m); reset() }} disabled={busy}
              className="px-4 py-1.5 text-[12px] font-medium capitalize transition-colors disabled:opacity-40"
              style={{ backgroundColor: mode === m ? C.cyan : "transparent", color: mode === m ? "#0A0B0F" : C.muted }}>
              {m}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 font-mono text-[11px]" style={{ color: C.muted }}>
          USER
          <input value={userId} onChange={(e) => setUserId(e.target.value)} disabled={busy}
            className="w-40 rounded-md bg-transparent px-2 py-1 text-[12px]" style={{ border: `1px solid ${C.faint}`, color: C.text }} />
        </label>
      </div>

      <div className="w-full max-w-xl rounded-2xl p-8" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
        {busy && countdown > 0 ? (
          <div className="text-center">
            <div className="font-mono text-[11px] tracking-[0.2em]" style={{ color: C.threat }}>● RECORDING · {countdown}s</div>
            {mode === "verify" && challenge && (
              <>
                <div className="mt-4 text-sm" style={{ color: C.muted }}>Read these digits, clearly:</div>
                <div className="mt-2 font-mono text-5xl font-bold tracking-[0.3em]" style={{ color: C.cyan }}>{challenge.split("").join(" ")}</div>
              </>
            )}
            {mode === "enroll" && prompts[slot] && (
              <>
                <div className="mt-4 text-sm" style={{ color: C.muted }}>Read prompt {slot + 1} of {prompts.length}:</div>
                <div className="mt-2 text-lg" style={{ color: C.text }}>"{prompts[slot]}"</div>
              </>
            )}
          </div>
        ) : busy ? (
          <div className="text-center font-mono text-sm animate-pulse" style={{ color: C.cyan }}>working…</div>
        ) : mode === "verify" && result ? (
          <div>
            <div className="text-center">
              <div className="font-mono font-bold text-4xl" style={{ color: verdictColor(result.verdict) }}>{result.verdict}</div>
              {result.reasons?.length ? <div className="mt-2 text-sm" style={{ color: C.text }}>{result.reasons.join(" · ")}</div> : null}
            </div>
            <div className="mt-6 grid grid-cols-2 gap-3 font-mono text-[12px]" style={{ color: C.muted }}>
              <div>voiceprint match <span style={{ color: (cosine ?? 0) >= 0.4 ? C.ok : C.threat }}>{cosine != null ? cosine.toFixed(3) : "—"}</span></div>
              <div>content <span style={{ color: result.scores?.content?.ok ? C.ok : C.threat }}>{result.scores?.content?.ok ? "match" : "—"}</span></div>
              <div>liveness <span style={{ color: C.text }}>{result.scores?.liveness?.bonafide_p ?? "—"}</span></div>
              <div>gate failed <span style={{ color: C.text }}>{result.gate_failed ?? "none"}</span></div>
            </div>
          </div>
        ) : mode === "enroll" && (prompts.length > 0 || enrollMsg) ? (
          <div className="text-center">
            {prompts[slot] && (
              <>
                <div className="text-sm" style={{ color: C.muted }}>Prompt {slot + 1} of {prompts.length}</div>
                <div className="mt-2 text-lg" style={{ color: C.text }}>"{prompts[slot]}"</div>
                <button onClick={recordEnrollSlot} disabled={busy}
                  className="mt-5 rounded-full px-6 py-2 text-sm font-medium" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                  ● Record slot {slot + 1}
                </button>
              </>
            )}
            {enrollMsg && <div className="mt-4 text-sm" style={{ color: enrollMsg.startsWith("✓") ? C.ok : C.warn }}>{enrollMsg}</div>}
          </div>
        ) : (
          <div className="text-center text-sm" style={{ color: C.muted }}>
            {mode === "verify"
              ? `Press Verify — you'll read ${VERIFY_MS / 1000}s of fresh digits.`
              : `Press Start enrollment — you'll read ${prompts.length || 3} short prompts.`}
          </div>
        )}
      </div>

      <button onClick={mode === "verify" ? startVerify : startEnroll} disabled={busy}
        className="rounded-full px-8 py-3 text-sm font-medium transition-colors disabled:opacity-40"
        style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
        {mode === "verify" ? (result ? "Verify again" : "Verify") : "Start enrollment"}
      </button>

      {error && <div className="font-mono text-[12px] text-center" style={{ color: C.threat }}>{error}</div>}

      <div className="font-mono text-[10px] text-center" style={{ color: C.muted }}>
        verify_app: {VERIFY_API} · set VITE_VERIFY_API_URL to change
      </div>
      <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
    </div>
  )
}
