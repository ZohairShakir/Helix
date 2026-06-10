/**
 * src/hooks/useHelixSocket.js
 * ----------------------------
 * Custom React hook that manages the WebSocket connection to the Helix backend.
 * Maintains a Map of run_id -> HelixRun objects.
 * Handles all server event types and auto-reconnects with exponential backoff.
 *
 * Exports:
 *   { runs, connected, selectedRunId, setSelectedRunId }
 */

import { useCallback, useEffect, useRef, useState } from 'react'

const WS_URL = 'ws://localhost:8000/ws'
const MAX_BACKOFF_MS = 30_000
const BASE_BACKOFF_MS = 1_000

export function useHelixSocket() {
  /** @type {[Map<string, object>, Function]} */
  const [runs, setRuns] = useState(new Map())
  const [connected, setConnected] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState(null)

  const wsRef = useRef(null)
  const backoffRef = useRef(BASE_BACKOFF_MS)
  const reconnectTimerRef = useRef(null)
  const isMountedRef = useRef(true)

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------

  const handleEvent = useCallback((event, data) => {
    setRuns((prev) => {
      const next = new Map(prev)

      switch (event) {
        case 'full_state': {
          // data is an array of all runs
          const arr = Array.isArray(data) ? data : []
          arr.forEach((run) => next.set(run.run_id, run))
          break
        }

        case 'run_created': {
          next.set(data.run_id, data)
          break
        }

        case 'trace_update': {
          const existing = next.get(data.run_id)
          if (existing) {
            next.set(data.run_id, { ...existing, trace: data.trace })
          }
          break
        }

        case 'diagnosis_ready': {
          const existing = next.get(data.run_id)
          if (existing) {
            next.set(data.run_id, { ...existing, diagnosis: data.diagnosis })
          }
          break
        }

        case 'fix_ready': {
          const existing = next.get(data.run_id)
          if (existing) {
            next.set(data.run_id, { ...existing, fix: data.fix })
          }
          break
        }

        case 'sandbox_result': {
          const existing = next.get(data.run_id)
          if (existing) {
            next.set(data.run_id, { ...existing, sandbox_output: data.sandbox_output })
          }
          break
        }

        case 'run_complete': {
          next.set(data.run_id, data)
          break
        }

        default:
          break
      }

      return next
    })
  }, [])

  // ---------------------------------------------------------------------------
  // Connection management
  // ---------------------------------------------------------------------------

  const connect = useCallback(() => {
    if (!isMountedRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (!isMountedRef.current) return
      setConnected(true)
      backoffRef.current = BASE_BACKOFF_MS // reset backoff on success
    }

    ws.onmessage = (evt) => {
      try {
        const { event, data } = JSON.parse(evt.data)
        if (event && event !== 'pong') {
          handleEvent(event, data)
        }
      } catch (err) {
        console.warn('[Helix WS] Failed to parse message:', err)
      }
    }

    ws.onclose = () => {
      if (!isMountedRef.current) return
      setConnected(false)

      // Schedule reconnect with exponential backoff
      const delay = backoffRef.current
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS)
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = (err) => {
      console.warn('[Helix WS] Connection error:', err)
      ws.close()
    }

    // Ping keepalive every 30s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30_000)

    // Cleanup ping when socket closes
    ws.addEventListener('close', () => clearInterval(pingInterval))
  }, [handleEvent])

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  useEffect(() => {
    isMountedRef.current = true
    connect()

    return () => {
      isMountedRef.current = false
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { runs, connected, selectedRunId, setSelectedRunId }
}
