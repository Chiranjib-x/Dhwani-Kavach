import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"
import { useWebSocket } from "@/hooks/use-websocket"
import { TARGET_SR } from "@/lib/audio-stream"

// Live-call demo: two devices join a room, establish a peer-to-peer WebRTC audio
// call (they hear each other), and the AGENT side taps the incoming voice track
// DIGITALLY into /ws/analyze — the same clean signal a real SIPREC tap would give,
// avoiding the over-the-air replay gap. 100% free: public STUN, our own signaling
// relay (/ws/rtc), no PSTN, no Twilio, no card.

export const Route = createFileRoute("/call")({ component: CallDemo })

const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000"
const WS = BACKEND.replace(/^http/, "ws")
const ICE: RTCIceServer[] = [{ urls: "stun:stun.l.google.com:19302" }]
const ROOM = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "").get("room") || "demo"

type Role = "customer" | "agent"
type AlertLevel = "GREEN" | "AMBER" | "RED" | "UNCERTAIN"
type Quality = { ok: boolean; score: number; reason: string; snr_db?: number }
type Action = "MONITOR" | "CHALLENGE" | "BLOCK"
type Result = {
  risk_score: number; alert_level: AlertLevel; call_max?: number
  quality?: Quality; action?: Action; action_reason?: string
}
type WsMsg = Result | { error: string }

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", faint: "rgba(255,255,255,0.08)" }
const levelColor = (l?: AlertLevel) => (l === "RED" ? C.threat : l === "AMBER" ? C.warn : l === "GREEN" ? C.ok : l === "UNCERTAIN" ? C.info : C.muted)
const actionColor = (a?: Action) => (a === "BLOCK" ? C.threat : a === "CHALLENGE" ? C.warn : C.ok)

function CallDemo() {
  const [role, setRole] = useState<Role | null>(null)
  if (!role) return <RolePicker onPick={setRole} />
  return <Call role={role} />
}

function RolePicker({ onPick }: { onPick: (r: Role) => void }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8 px-6" style={{ backgroundColor: "#0A0B0F", color: C.text }}>
      <div className="text-center">
        <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · LIVE CALL</div>
        <h1 className="mt-3 text-3xl font-semibold">Pick your side of the call</h1>
        <p className="mt-2 text-sm" style={{ color: C.muted }}>Open this page on two devices (or two tabs). Room: <span className="font-mono">{ROOM}</span></p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 w-full max-w-2xl">
        <button onClick={() => onPick("customer")} className="rounded-2xl p-8 text-left transition-colors"
          style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="text-2xl">📞</div>
          <div className="mt-3 text-lg font-semibold">I'm the Customer</div>
          <div className="mt-1 text-sm" style={{ color: C.muted }}>Place the call. Your microphone becomes the caller's voice.</div>
        </button>
        <button onClick={() => onPick("agent")} className="rounded-2xl p-8 text-left transition-colors"
          style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="text-2xl">🛡️</div>
          <div className="mt-3 text-lg font-semibold">I'm the Bank Agent</div>
          <div className="mt-1 text-sm" style={{ color: C.muted }}>Monitor the call. Dhwani scores the caller's voice live.</div>
        </button>
      </div>
    </div>
  )
}

/** Shared signaling + peer-connection wiring. Customer is the offerer, agent the answerer. */
function Call({ role }: { role: Role }) {
  const [callState, setCallState] = useState("connecting to room…")
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null)
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const sigRef = useRef<WebSocket | null>(null)
  const pendingIce = useRef<RTCIceCandidateInit[]>([])
  const offered = useRef(false)

  const sig = useCallback((obj: unknown) => {
    const ws = sigRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj))
  }, [])

  useEffect(() => {
    let disposed = false
    const pc = new RTCPeerConnection({ iceServers: ICE })
    pcRef.current = pc
    pc.onicecandidate = (e) => { if (e.candidate) sig({ type: "ice", candidate: e.candidate.toJSON() }) }
    pc.onconnectionstatechange = () => { if (!disposed) setCallState(`call: ${pc.connectionState}`) }
    pc.ontrack = (e) => { if (!disposed) setRemoteStream(e.streams[0]) }

    const makeOffer = async () => {
      if (offered.current) return
      offered.current = true
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      sig({ type: "offer", sdp: offer.sdp })
    }

    const start = async () => {
      if (role === "customer") {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
          })
          stream.getTracks().forEach((t) => pc.addTrack(t, stream))
          setCallState("mic ready — waiting for the agent…")
        } catch {
          setCallState("microphone blocked — allow mic access and reload")
          return
        }
      } else {
        // agent receives only
        pc.addTransceiver("audio", { direction: "recvonly" })
      }

      const ws = new WebSocket(`${WS}/ws/rtc/${ROOM}`)
      sigRef.current = ws
      ws.onmessage = async (ev) => {
        const m = JSON.parse(ev.data)
        if (m.type === "joined") {
          if (role === "customer" && m.peers > 0) await makeOffer()
        } else if (m.type === "peer-joined") {
          if (role === "customer") await makeOffer()
        } else if (m.type === "peer-left") {
          offered.current = false
          setRemoteStream(null)
          setCallState("the other side hung up")
        } else if (m.type === "full") {
          setCallState("room is full (two devices already connected)")
        } else if (m.type === "offer" && role === "agent") {
          await pc.setRemoteDescription({ type: "offer", sdp: m.sdp })
          for (const c of pendingIce.current) await pc.addIceCandidate(c).catch(() => {})
          pendingIce.current = []
          const answer = await pc.createAnswer()
          await pc.setLocalDescription(answer)
          sig({ type: "answer", sdp: answer.sdp })
        } else if (m.type === "answer" && role === "customer") {
          await pc.setRemoteDescription({ type: "answer", sdp: m.sdp })
          for (const c of pendingIce.current) await pc.addIceCandidate(c).catch(() => {})
          pendingIce.current = []
        } else if (m.type === "ice") {
          if (pc.remoteDescription) await pc.addIceCandidate(m.candidate).catch(() => {})
          else pendingIce.current.push(m.candidate)
        }
      }
      ws.onclose = () => { if (!disposed) setCallState("signaling disconnected") }
    }
    void start()

    return () => {
      disposed = true
      sigRef.current?.close()
      pcRef.current?.getSenders().forEach((s) => s.track?.stop())
      pcRef.current?.close()
    }
  }, [role, sig])

  return role === "customer"
    ? <CustomerView state={callState} />
    : <AgentView state={callState} remoteStream={remoteStream} />
}

function CustomerView({ state }: { state: string }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-6 text-center" style={{ backgroundColor: "#0A0B0F", color: C.text }}>
      <div className="text-6xl">📞</div>
      <h1 className="text-2xl font-semibold">You're the caller</h1>
      <p className="text-sm max-w-md" style={{ color: C.muted }}>
        Speak normally — the bank agent's screen scores your voice live. To demo a
        deepfake, play an AI-cloned clip into this device's mic input.
      </p>
      <div className="font-mono text-[12px] rounded-full px-4 py-2" style={{ border: `1px solid ${C.faint}`, color: C.cyan }}>{state}</div>
    </div>
  )
}

/** Agent console (this also covers C2): taps the caller's WebRTC track into /ws/analyze. */
function AgentView({ state, remoteStream }: { state: string; remoteStream: MediaStream | null }) {
  const [result, setResult] = useState<Result | null>(null)
  const [alerts, setAlerts] = useState<{ id: number; t: string; level: AlertLevel; risk: number }[]>([])
  const seq = useRef(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const onMessage = useCallback((m: WsMsg) => {
    if ("error" in m) return
    setResult(m)
    setAlerts((a) => [{ id: ++seq.current, t: new Date().toLocaleTimeString(), level: m.alert_level, risk: m.risk_score }, ...a].slice(0, 10))
  }, [])
  const { status, send } = useWebSocket<WsMsg>(`${WS}/ws/analyze`, onMessage)

  // Attach the remote stream to an <audio> (so the agent hears the caller AND so
  // the browser actually delivers samples to the tap) and pump 16 kHz PCM to /ws/analyze.
  useEffect(() => {
    if (!remoteStream) return
    if (audioRef.current) audioRef.current.srcObject = remoteStream
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ac = new AC({ sampleRate: TARGET_SR })
    const src = ac.createMediaStreamSource(remoteStream)
    const proc = ac.createScriptProcessor(4096, 1, 1)
    proc.onaudioprocess = (e) => send(e.inputBuffer.getChannelData(0).slice().buffer)
    src.connect(proc)
    proc.connect(ac.destination) // required to fire onaudioprocess; writes silence, no echo
    return () => { proc.disconnect(); src.disconnect(); ac.close().catch(() => {}) }
  }, [remoteStream, send])

  const risk = result?.risk_score ?? 0
  const level = remoteStream ? result?.alert_level : undefined
  const color = levelColor(level)
  const R = 90, CIRC = Math.PI * R

  return (
    <div className="min-h-screen px-6 py-8" style={{ backgroundColor: "#0A0B0F", color: C.text }}>
      <div className="mx-auto max-w-3xl">
        {/* caller strip */}
        <div className="flex items-center justify-between rounded-xl px-5 py-3" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="flex items-center gap-3">
            <span className="text-xl">👤</span>
            <div>
              <div className="text-sm font-semibold">Incoming caller</div>
              <div className="font-mono text-[11px]" style={{ color: C.muted }}>+91 ·· ···· ·· · room {ROOM}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px]" style={{ color: C.muted }}>
            <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ backgroundColor: status === "open" ? C.ok : C.warn }} />
            {remoteStream ? "CALL LIVE · SCORING" : state}
          </div>
        </div>

        {/* quality abstention banner */}
        {result?.quality && !result.quality.ok && remoteStream && (
          <div className="mt-4 rounded-xl px-5 py-3 flex items-center gap-3" style={{ border: `1px solid ${C.info}`, backgroundColor: "rgba(56,189,248,0.06)" }}>
            <span className="font-mono text-[13px]" style={{ color: C.info }}>◑ INPUT QUALITY LOW</span>
            <span className="text-[13px]">{result.quality.reason}</span>
            <span className="font-mono text-[11px] ml-auto" style={{ color: C.muted }}>verdict held · verify caller</span>
          </div>
        )}

        {/* verdict */}
        <div className="mt-4 grid gap-6 sm:grid-cols-[auto_1fr] items-center rounded-2xl p-8" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="flex flex-col items-center">
            <svg width="220" height="130" viewBox="0 0 220 130">
              <path d={`M 20 110 A ${R} ${R} 0 0 1 200 110`} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" strokeLinecap="round" />
              <path d={`M 20 110 A ${R} ${R} 0 0 1 200 110`} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
                strokeDasharray={CIRC} strokeDashoffset={CIRC * (1 - risk / 100)} style={{ transition: "stroke-dashoffset 0.5s, stroke 0.4s" }} />
            </svg>
            <div className="-mt-6 text-center">
              <div className="font-mono font-bold text-[52px] leading-none" style={{ color }}>{String(risk).padStart(2, "0")}</div>
              <div className="mt-2 font-mono text-[11px] tracking-[0.2em]" style={{ color }}>
                {remoteStream ? (level ?? "LISTENING…") : "WAITING FOR CALL"}
              </div>
            </div>
          </div>
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em]" style={{ color: C.muted }}>RECOMMENDED ACTION</div>
            <div className="mt-1 font-mono font-bold text-[22px]" style={{ color: actionColor(result?.action) }}>{result?.action ?? "—"}</div>
            <div className="mt-2 text-[13px]" style={{ color: C.muted }}>
              {result?.action_reason || "Fraud shield listens to the live call and flags a synthetic voice before the money moves."}
            </div>
          </div>
        </div>

        {/* history */}
        <div className="mt-4 rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div className="font-mono text-[11px] tracking-wider mb-3" style={{ color: C.muted }}>LIVE SCORES</div>
          <div className="max-h-44 overflow-y-auto space-y-1.5">
            {alerts.length === 0 && <div className="font-mono text-[11px]" style={{ color: C.muted }}>waiting for the caller to speak…</div>}
            {alerts.map((a) => (
              <div key={a.id} className="grid grid-cols-[80px_1fr_auto] items-center gap-3 font-mono text-[11px]" style={{ color: C.muted }}>
                <span>{a.t}</span><span>window scored</span>
                <span style={{ color: levelColor(a.level) }}>{a.level} · {a.risk}</span>
              </div>
            ))}
          </div>
        </div>
        <audio ref={audioRef} autoPlay className="hidden" />
      </div>
    </div>
  )
}
