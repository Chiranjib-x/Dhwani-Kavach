import { useCallback, useEffect, useRef, useState } from "react"

export type WsStatus = "connecting" | "open" | "closed"

const MAX_RETRIES = 6
const RETRY_MS = 1500

/**
 * Binary WebSocket with auto-connect on mount, capped auto-reconnect, and a
 * send queue that buffers frames until the socket is open. JSON messages are
 * parsed and handed to `onMessage`.
 */
export function useWebSocket<T = unknown>(url: string, onMessage?: (msg: T) => void) {
  const [status, setStatus] = useState<WsStatus>("connecting")
  const wsRef = useRef<WebSocket | null>(null)
  const queue = useRef<ArrayBuffer[]>([])
  const retries = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const disposed = useRef(false)
  const onMsg = useRef(onMessage)
  onMsg.current = onMessage

  const connect = useCallback(() => {
    if (disposed.current) return
    setStatus("connecting")
    const ws = new WebSocket(url)
    ws.binaryType = "arraybuffer"
    wsRef.current = ws

    ws.onopen = () => {
      retries.current = 0
      setStatus("open")
      for (const buf of queue.current) ws.send(buf)
      queue.current = []
    }
    ws.onmessage = (e) => {
      try {
        onMsg.current?.(JSON.parse(e.data) as T)
      } catch {
        /* non-JSON frame — ignore */
      }
    }
    ws.onerror = () => ws.close()
    ws.onclose = () => {
      setStatus("closed")
      if (disposed.current || retries.current >= MAX_RETRIES) return
      retries.current += 1
      timer.current = setTimeout(connect, RETRY_MS)
    }
  }, [url])

  useEffect(() => {
    disposed.current = false
    connect()
    return () => {
      disposed.current = true
      if (timer.current) clearTimeout(timer.current)
      wsRef.current?.close()
    }
  }, [connect])

  /** Force a fresh connection — used when the user starts an analysis after retries gave up. */
  const reconnect = useCallback(() => {
    retries.current = 0
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return
    connect()
  }, [connect])

  const send = useCallback((data: ArrayBuffer) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(data)
    else queue.current.push(data)
  }, [])

  return { status, send, reconnect }
}
