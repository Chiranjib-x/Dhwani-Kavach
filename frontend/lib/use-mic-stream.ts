"use client"

import { useCallback, useRef } from "react"
import { TARGET_SR } from "./audio-stream"

/**
 * Capture the microphone as 16 kHz mono float32 PCM frames and hand each frame
 * to `onFrame` (ready to ship over /ws/analyze). Returns the live AnalyserNode
 * from start() so the caller can draw a spectrogram.
 */
export function useMicStream(onFrame: (frame: ArrayBuffer) => void) {
  const cb = useRef(onFrame)
  cb.current = onFrame
  const acRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const start = useCallback(async (): Promise<AnalyserNode> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false },
    })
    streamRef.current = stream

    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ac = new AC({ sampleRate: TARGET_SR }) // browser resamples the mic to 16 kHz
    acRef.current = ac

    const src = ac.createMediaStreamSource(stream)
    const analyser = ac.createAnalyser()
    analyser.fftSize = 256
    // ponytail: ScriptProcessor is deprecated but a one-liner for raw PCM;
    // swap to an AudioWorklet only if a browser actually drops it.
    const proc = ac.createScriptProcessor(4096, 1, 1)
    proc.onaudioprocess = (e) => cb.current(e.inputBuffer.getChannelData(0).slice().buffer)

    src.connect(analyser)
    analyser.connect(proc)
    proc.connect(ac.destination) // required to fire onaudioprocess; we never write output, so no echo
    return analyser
  }, [])

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    acRef.current?.close().catch(() => {})
    streamRef.current = null
    acRef.current = null
  }, [])

  return { start, stop }
}
