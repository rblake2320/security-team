import { useCallback, useEffect, useRef, useState } from 'react'
import type { Engagement, EngagementCreateInput, GateRun, RetentionInput, RunComparison, SafetyLevel, ShadowAIPolicyInput, Snapshot } from './types'

interface MissionState {
  snapshot: Snapshot | null
  engagements: Engagement[]
  connected: boolean
  error: string | null
  runGate: (gateId: string, mode?: 'engineering' | 'assurance') => Promise<GateRun>
  refresh: () => Promise<void>
  decideTask: (taskId: string, decision: 'approved' | 'rejected') => Promise<void>
  decideAsset: (assetId: string, disposition: 'approved' | 'restricted' | 'blocked') => Promise<void>
  decideViolation: (violationId: string, status: 'acknowledged' | 'resolved' | 'false-positive') => Promise<void>
  updateShadowPolicy: (policy: ShadowAIPolicyInput) => Promise<void>
  updateRetention: (retention: RetentionInput) => Promise<void>
  updateSafety: (level: SafetyLevel, reason: string) => Promise<void>
  provisionConnector: (name: string, capabilities: string[]) => Promise<{ token: string; warning: string }>
  createEngagement: (input: EngagementCreateInput) => Promise<Engagement>
  uploadEngagementAssets: (engagementId: string, files: File[]) => Promise<void>
  launchEngagement: (engagementId: string, mode: 'safe' | 'standard' | 'deep', connectorId?: string, baselineRunId?: string) => Promise<void>
  analyzeEngagementAsset: (engagementId: string, assetId: string, connectorId?: string) => Promise<void>
  compareEngagementRuns: (engagementId: string, baselineRunId: string, currentRunId: string) => Promise<RunComparison>
}

export function useMissionControl(): MissionState {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [engagements, setEngagements] = useState<Engagement[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSource = useRef<EventSource | null>(null)

  const fetchSnapshot = useCallback(async (): Promise<Snapshot> => {
    const response = await fetch('/api/snapshot', { cache: 'no-store', credentials: 'same-origin' })
    if (!response.ok) throw new Error(`Snapshot request failed (${response.status})`)
    const next = (await response.json()) as Snapshot
    setSnapshot(next)
    setConnected(true)
    setError(null)
    if (next.deployment.mode === 'saas') {
      const engagementResponse = await fetch('/api/v1/engagements', { cache: 'no-store', credentials: 'same-origin' })
      if (engagementResponse.ok) {
        const engagementPayload = (await engagementResponse.json()) as { engagements: Engagement[] }
        setEngagements(engagementPayload.engagements)
      }
    } else {
      setEngagements([])
    }
    return next
  }, [])

  const refresh = useCallback(async () => { await fetchSnapshot() }, [fetchSnapshot])

  useEffect(() => {
    let polling: number | undefined
    let cancelled = false
    void fetchSnapshot().then((initial) => {
      if (cancelled) return
      if (initial.deployment.streamingEnabled) {
        const stream = new EventSource('/api/stream', { withCredentials: true })
        eventSource.current = stream
        stream.addEventListener('snapshot', (event) => {
          setSnapshot(JSON.parse((event as MessageEvent<string>).data) as Snapshot)
          setConnected(true)
          setError(null)
        })
        stream.onerror = () => {
          setConnected(false)
          setError('Live stream reconnecting')
        }
      } else {
        polling = window.setInterval(() => {
          void fetchSnapshot().catch((reason: unknown) => {
            setConnected(false)
            setError(reason instanceof Error ? reason.message : 'Unable to refresh')
          })
        }, 5000)
      }
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to connect'))
    return () => {
      cancelled = true
      if (polling) window.clearInterval(polling)
      eventSource.current?.close()
    }
  }, [fetchSnapshot])

  const runGate = useCallback(async (gateId: string, mode: 'engineering' | 'assurance' = 'engineering') => {
    const response = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        gateId,
        mode,
        ...(mode === 'assurance' ? { confirmation: 'RUN_FAIL_CLOSED_READINESS_CHECK' } : {}),
      }),
    })
    const payload = (await response.json()) as { run?: GateRun; error?: string }
    if (!response.ok || !payload.run) throw new Error(payload.error ?? 'Run request failed')
    await refresh()
    return payload.run
  }, [refresh])

  const controlRequest = useCallback(async (path: string, body: unknown, method: 'POST' | 'PUT' = 'POST') => {
    const response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as { detail?: string }
      throw new Error(payload.detail ?? `Control request failed (${response.status})`)
    }
    await refresh()
  }, [refresh])

  const decideTask = useCallback(
    (taskId: string, decision: 'approved' | 'rejected') => controlRequest(
      `/api/v1/tasks/${encodeURIComponent(taskId)}/decision`,
      { decision, note: `${decision === 'approved' ? 'Approved' : 'Rejected'} from the Mission Control review queue.` },
    ),
    [controlRequest],
  )

  const decideAsset = useCallback(
    (assetId: string, disposition: 'approved' | 'restricted' | 'blocked') => controlRequest(
      `/api/v1/shadow-ai/assets/${encodeURIComponent(assetId)}/decision`,
      { disposition, reason: `Operator classified this AI asset as ${disposition}.` },
    ),
    [controlRequest],
  )

  const decideViolation = useCallback(
    (violationId: string, status: 'acknowledged' | 'resolved' | 'false-positive') => controlRequest(
      `/api/v1/shadow-ai/violations/${encodeURIComponent(violationId)}/decision`,
      { status, note: `Operator marked this policy violation ${status}.` },
    ),
    [controlRequest],
  )

  const updateShadowPolicy = useCallback(
    (policy: ShadowAIPolicyInput) => controlRequest('/api/v1/shadow-ai/policy', policy, 'PUT'),
    [controlRequest],
  )

  const updateRetention = useCallback(
    (retention: RetentionInput) => controlRequest('/api/v1/retention', retention, 'PUT'),
    [controlRequest],
  )

  const updateSafety = useCallback(
    (level: SafetyLevel, reason: string) => controlRequest('/api/v1/safety', { level, reason }),
    [controlRequest],
  )

  const provisionConnector = useCallback(async (name: string, capabilities: string[]) => {
    const response = await fetch('/api/v1/connectors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ name, capabilities }),
    })
    const payload = (await response.json().catch(() => ({}))) as { token?: string; warning?: string; detail?: string }
    if (!response.ok || !payload.token) throw new Error(payload.detail ?? `Connector provisioning failed (${response.status})`)
    await refresh()
    return { token: payload.token, warning: payload.warning ?? 'This credential is shown once.' }
  }, [refresh])

  const createEngagement = useCallback(async (input: EngagementCreateInput) => {
    const response = await fetch('/api/v1/engagements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(input),
    })
    const payload = (await response.json().catch(() => ({}))) as { engagement?: Engagement; detail?: string }
    if (!response.ok || !payload.engagement) throw new Error(payload.detail ?? `Engagement creation failed (${response.status})`)
    await refresh()
    return payload.engagement
  }, [refresh])

  const uploadEngagementAssets = useCallback(async (engagementId: string, files: File[]) => {
    for (const file of files) {
      const body = new FormData()
      body.append('engagementId', engagementId)
      body.append('classification', 'customer-confidential')
      body.append('file', file)
      const response = await fetch('/api/v1/evidence', { method: 'POST', credentials: 'same-origin', body })
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as { detail?: string }
        throw new Error(payload.detail ?? `${file.name} upload failed (${response.status})`)
      }
    }
    await refresh()
  }, [refresh])

  const launchEngagement = useCallback(async (
    engagementId: string,
    mode: 'safe' | 'standard' | 'deep',
    connectorId?: string,
    baselineRunId?: string,
  ) => {
    const response = await fetch(`/api/v1/engagements/${encodeURIComponent(engagementId)}/launch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ mode, connectorId: connectorId || undefined, baselineRunId: baselineRunId || undefined }),
    })
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as { detail?: string }
      throw new Error(payload.detail ?? `Assessment launch failed (${response.status})`)
    }
    await refresh()
  }, [refresh])

  const compareEngagementRuns = useCallback(async (engagementId: string, baselineRunId: string, currentRunId: string) => {
    const parameters = new URLSearchParams({ baselineRunId, currentRunId })
    const response = await fetch(`/api/v1/engagements/${encodeURIComponent(engagementId)}/compare?${parameters}`, {
      cache: 'no-store',
      credentials: 'same-origin',
    })
    const payload = (await response.json().catch(() => ({}))) as RunComparison & { detail?: string }
    if (!response.ok) throw new Error(payload.detail ?? `Run comparison failed (${response.status})`)
    return payload
  }, [])

  const analyzeEngagementAsset = useCallback(async (engagementId: string, assetId: string, connectorId?: string) => {
    const response = await fetch(`/api/v1/engagements/${encodeURIComponent(engagementId)}/assets/${encodeURIComponent(assetId)}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ connectorId: connectorId || undefined }),
    })
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as { detail?: string }
      throw new Error(payload.detail ?? `Asset analysis failed (${response.status})`)
    }
    await refresh()
  }, [refresh])

  return { snapshot, engagements, connected, error, runGate, refresh, decideTask, decideAsset, decideViolation, updateShadowPolicy, updateRetention, updateSafety, provisionConnector, createEngagement, uploadEngagementAssets, launchEngagement, analyzeEngagementAsset, compareEngagementRuns }
}
