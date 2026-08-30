import { useCallback } from 'react'
import type { MissionState } from './api-types'
import { useSnapshotFeed } from './snapshot'
import type { Engagement, EngagementCreateInput, GateRun, RetentionInput, RunComparison, SafetyLevel, ShadowAIPolicyInput, Snapshot } from './types'

export function useMissionControl(): MissionState {
  const loadEngagements = useCallback(async (_snapshot: Snapshot) => {
    const response = await fetch('/api/v1/engagements', { cache: 'no-store', credentials: 'same-origin' })
    if (!response.ok) return []
    const payload = (await response.json()) as { engagements: Engagement[] }
    return payload.engagements
  }, [])
  const { snapshot, engagements, connected, error, refresh, retryInitial } = useSnapshotFeed(loadEngagements)

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

  const engagementExportUrl = useCallback((engagementId: string) => `/api/v1/engagements/${encodeURIComponent(engagementId)}/export`, [])
  const evidenceDownloadUrl = useCallback((evidenceId: string) => `/api/v1/evidence/${encodeURIComponent(evidenceId)}/download`, [])

  return { snapshot, engagements, connected, error, retryInitial, runGate, refresh, decideTask, decideAsset, decideViolation, updateShadowPolicy, updateRetention, updateSafety, provisionConnector, createEngagement, uploadEngagementAssets, launchEngagement, analyzeEngagementAsset, compareEngagementRuns, engagementExportUrl, evidenceDownloadUrl }
}
