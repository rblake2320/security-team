import type {
  Engagement,
  EngagementCreateInput,
  GateRun,
  RetentionInput,
  RunComparison,
  SafetyLevel,
  ShadowAIPolicyInput,
  Snapshot,
} from './types'

export interface MissionState {
  snapshot: Snapshot | null
  engagements: Engagement[]
  connected: boolean
  error: string | null
  retryInitial: () => void
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
  engagementExportUrl: (engagementId: string) => string | null
  evidenceDownloadUrl: (evidenceId: string) => string | null
}
