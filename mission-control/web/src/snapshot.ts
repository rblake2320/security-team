import { useCallback, useEffect, useRef, useState } from 'react'
import type { Engagement, Snapshot } from './types'

const SNAPSHOT_TIMEOUT_MS = 10_000
const INITIAL_RETRY_DELAYS_MS = [1_000, 2_000] as const
export const SNAPSHOT_UNAVAILABLE_MESSAGE = 'The secure status feed is temporarily unavailable. No controls or assurance data have been loaded.'

type EngagementLoader = (snapshot: Snapshot) => Promise<Engagement[]>

interface SnapshotFeed {
  snapshot: Snapshot | null
  engagements: Engagement[]
  connected: boolean
  error: string | null
  refresh: () => Promise<void>
  retryInitial: () => void
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSnapshot(value: unknown): value is Snapshot {
  if (!isRecord(value) || typeof value.generatedAt !== 'string') return false
  const deployment = value.deployment
  const program = value.program
  const repo = value.repo
  const gates = value.gates
  const agents = value.agents
  const ledger = value.controlLedger
  return isRecord(deployment)
    && ['operator', 'demo', 'saas'].includes(String(deployment.mode))
    && typeof deployment.controlsEnabled === 'boolean'
    && typeof deployment.streamingEnabled === 'boolean'
    && isRecord(program)
    && Array.isArray(program.gates)
    && isRecord(repo)
    && isRecord(gates)
    && Array.isArray(gates.engineering)
    && Array.isArray(value.teams)
    && isRecord(agents)
    && Array.isArray(agents.sessions)
    && Array.isArray(value.runs)
    && Array.isArray(value.activity)
    && isRecord(ledger)
}

export function useSnapshotFeed(loadEngagements?: EngagementLoader): SnapshotFeed {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [engagements, setEngagements] = useState<Engagement[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bootstrapVersion, setBootstrapVersion] = useState(0)
  const eventSource = useRef<EventSource | null>(null)
  const activeRequest = useRef<AbortController | null>(null)

  const fetchSnapshot = useCallback(async (): Promise<Snapshot> => {
    activeRequest.current?.abort()
    const controller = new AbortController()
    activeRequest.current = controller
    const timeout = window.setTimeout(() => controller.abort(), SNAPSHOT_TIMEOUT_MS)
    try {
      const response = await fetch('/api/snapshot', {
        cache: 'no-store',
        credentials: 'same-origin',
        signal: controller.signal,
      })
      if (!response.ok) throw new Error(`Snapshot request failed (${response.status})`)
      const payload: unknown = await response.json()
      if (!isSnapshot(payload)) throw new Error('Snapshot response failed validation')
      const nextEngagements = loadEngagements && payload.deployment.mode === 'saas'
        ? await loadEngagements(payload)
        : []
      setSnapshot(payload)
      setEngagements(nextEngagements)
      setConnected(true)
      setError(null)
      return payload
    } finally {
      window.clearTimeout(timeout)
      if (activeRequest.current === controller) activeRequest.current = null
    }
  }, [loadEngagements])

  const refresh = useCallback(async () => {
    try {
      await fetchSnapshot()
    } catch (reason: unknown) {
      setConnected(false)
      setError(SNAPSHOT_UNAVAILABLE_MESSAGE)
      throw reason
    }
  }, [fetchSnapshot])

  const retryInitial = useCallback(() => {
    activeRequest.current?.abort()
    setError(null)
    setBootstrapVersion((current) => current + 1)
  }, [])

  useEffect(() => {
    let polling: number | undefined
    let retryTimer: number | undefined
    let cancelled = false

    const waitForRetry = (delay: number) => new Promise<void>((resolve) => {
      retryTimer = window.setTimeout(resolve, delay)
    })

    const bootstrap = async () => {
      for (let attempt = 0; attempt <= INITIAL_RETRY_DELAYS_MS.length; attempt += 1) {
        try {
          const initial = await fetchSnapshot()
          if (cancelled) return
          if (initial.deployment.streamingEnabled) {
            const stream = new EventSource('/api/stream', { withCredentials: true })
            eventSource.current = stream
            stream.addEventListener('snapshot', (event) => {
              try {
                const payload: unknown = JSON.parse((event as MessageEvent<string>).data)
                if (!isSnapshot(payload)) throw new Error('Snapshot event failed validation')
                setSnapshot(payload)
                setConnected(true)
                setError(null)
              } catch {
                setConnected(false)
                setError(SNAPSHOT_UNAVAILABLE_MESSAGE)
              }
            })
            stream.onerror = () => {
              setConnected(false)
              setError(SNAPSHOT_UNAVAILABLE_MESSAGE)
            }
          } else {
            polling = window.setInterval(() => {
              void refresh().catch(() => undefined)
            }, 5_000)
          }
          return
        } catch {
          if (cancelled) return
          setConnected(false)
          setError(SNAPSHOT_UNAVAILABLE_MESSAGE)
          if (attempt === INITIAL_RETRY_DELAYS_MS.length) return
          await waitForRetry(INITIAL_RETRY_DELAYS_MS[attempt])
          if (cancelled) return
        }
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
      if (polling) window.clearInterval(polling)
      if (retryTimer) window.clearTimeout(retryTimer)
      activeRequest.current?.abort()
      eventSource.current?.close()
      eventSource.current = null
    }
  }, [bootstrapVersion, fetchSnapshot, refresh])

  return { snapshot, engagements, connected, error, refresh, retryInitial }
}
