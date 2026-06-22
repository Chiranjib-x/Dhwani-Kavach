// Decode + resample audio entirely with native Web Audio — no FFT/resample libs.

export const TARGET_SR = 16000

type AudioCtor = typeof AudioContext

function audioCtor(): AudioCtor {
  const w = window as unknown as { AudioContext?: AudioCtor; webkitAudioContext?: AudioCtor }
  const AC = w.AudioContext ?? w.webkitAudioContext
  if (!AC) throw new Error("Web Audio API not supported in this browser.")
  return AC
}

/** File → mono Float32 PCM resampled to 16 kHz (what /ws/analyze expects). */
export async function decodeTo16kMono(file: File): Promise<Float32Array> {
  const bytes = await file.arrayBuffer()
  const tmp = new (audioCtor())()
  const decoded = await tmp.decodeAudioData(bytes)
  tmp.close()

  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET_SR), TARGET_SR)
  const src = offline.createBufferSource()
  src.buffer = decoded
  src.connect(offline.destination)
  src.start()
  const rendered = await offline.startRendering()
  return rendered.getChannelData(0).slice()
}

/**
 * Stream PCM to a sink in fixed frames, paced ~4x real time so the dashboard
 * visibly updates window-by-window. Returns when the whole clip is sent or aborted.
 */
export async function streamPcm(
  pcm: Float32Array,
  send: (frame: ArrayBuffer) => void,
  opts: { frame?: number; pacing?: boolean; signal?: AbortSignal } = {},
): Promise<void> {
  const frame = opts.frame ?? 8000 // 0.5s @ 16 kHz
  for (let i = 0; i < pcm.length; i += frame) {
    if (opts.signal?.aborted) return
    send(pcm.slice(i, i + frame).buffer)
    if (opts.pacing !== false) await new Promise((r) => setTimeout(r, 125))
  }
}
