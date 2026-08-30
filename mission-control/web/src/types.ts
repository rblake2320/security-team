export type RunStatus = 'not_run' | 'queued' | 'running' | 'passed' | 'failed' | 'awaiting_approval' | 'rejected' | 'blocked' | 'succeeded'

export interface PlatformTask {
  id: string
  title: string
  action: string
  riskLevel: string
  status: string
  dryRun: boolean
  approvalRequired: boolean
  createdAt: string
  completedAt: string | null
}

export interface PlatformApproval {
  id: string
  taskId: string
  status: string
  reason: string
  expiresAt: string
  createdAt: string
}

export interface SecurityControl {
  id: string
  key: string
  title: string
  domain: string
  ownerTeam: string
  objective: string
  modes: string[]
  requiredSource: string
  status: 'verified' | 'configured' | 'telemetry-gap' | 'exception' | 'disabled'
  enabled: boolean
}

export interface SecurityCoverage {
  summary: {
    controls: number
    enabled: number
    observable: number
    verified: number
    telemetryGaps: number
    exceptions: number
    coveragePercent: number
  }
  sources: string[]
  teams: Array<{ team: string; controls: number; verified: number; gaps: number }>
  controls: SecurityControl[]
}

export interface ShadowAIAsset {
  id: string
  source: string
  externalId: string
  name: string
  vendor: string
  category: string
  disposition: 'unknown' | 'approved' | 'restricted' | 'blocked'
  riskScore: number
  models: string[]
  tools: string[]
  mcpServers: string[]
  resources: string[]
  lastSeenAt: string
}

export interface ShadowAIViolation {
  id: string
  assetId: string
  ruleId: string
  severity: string
  disposition: string
  status: string
  summary: string
  detail: Record<string, unknown>
  createdAt: string
}

export interface ShadowAIData {
  counts: {
    assets: number
    unsanctioned: number
    blocked: number
    openViolations: number
    usageEvents: number
    bytesSent: number
    estimatedCostMicrousd: number
  }
  assets: ShadowAIAsset[]
  violations: ShadowAIViolation[]
  policy: {
    defaultDisposition: string
    sensitiveDataDisposition: string
    approvedVendors: string[]
    approvedDomains: string[]
    blockedDomains: string[]
    prohibitedDataLabels: string[]
    retainPromptContent: boolean
  }
}

export interface ShadowAIPolicyInput {
  defaultDisposition: 'monitor' | 'require-approval' | 'block'
  sensitiveDataDisposition: 'monitor' | 'require-approval' | 'block'
  approvedVendors: string[]
  approvedDomains: string[]
  blockedDomains: string[]
  prohibitedDataLabels: string[]
  retainPromptContent: false
}

export interface RetentionInput {
  telemetryDays: number
  taskDays: number
  evidenceDays: number
  auditDays: number
  legalHoldDefault: boolean
}

export type SafetyLevel = 'normal' | 'cautious' | 'restricted' | 'halted'

export type SecurityTeam = 'purple' | 'white' | 'yellow' | 'green' | 'orange' | 'blue' | 'red'

export interface EngagementTarget {
  id: string
  kind: string
  displayName: string
  locator: string
  environment: string
  scopeStatus: string
  notes: string
}

export interface AssessmentRun {
  id: string
  sequence: number
  mode: 'safe' | 'standard' | 'deep'
  status: string
  connectorId: string | null
  taskId: string | null
  baselineRunId: string | null
  teamPlan: {
    targetKinds?: string[]
    teams?: Array<{ id: SecurityTeam; verb: string; checks: string[] }>
    rules?: string[]
  }
  summary: Record<string, unknown>
  recommendations: Array<Record<string, unknown>>
  score: number | null
  createdAt: string
  startedAt: string | null
  completedAt: string | null
}

export interface EngagementAsset {
  id: string
  evidenceId: string
  assessmentRunId: string | null
  filename: string
  contentType: string
  sizeBytes: number
  sha256: string
  classification: string
  scanStatus: string
  mediaKind: string
  analysisStatus: string
  suggestions: Array<{ team: SecurityTeam; title: string; detail: string }>
  createdAt: string
}

export interface EngagementFinding {
  id: string
  assessmentRunId: string | null
  fingerprint: string | null
  ownerTeam: SecurityTeam | null
  title: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: string
  createdAt: string
}

export interface Engagement {
  id: string
  name: string
  clientName: string | null
  engagementType: string
  status: string
  objective: string
  scopeRules: string
  authorization: {
    basis: string
    confirmed: boolean
    attestation: string
    authorizedAt: string | null
    expiresAt: string | null
  }
  selectedTeams: SecurityTeam[]
  targets: EngagementTarget[]
  runs: AssessmentRun[]
  assets: EngagementAsset[]
  findings: EngagementFinding[]
  createdAt: string
  updatedAt: string
}

export interface EngagementCreateInput {
  name: string
  clientName?: string
  engagementType: 'own-site' | 'pre-launch' | 'client-assessment' | 'continuous' | 'incident' | 'other'
  objective: string
  scopeRules: string
  authorizationBasis: 'asset-owner' | 'internal-approval' | 'written-client-authorization' | 'bug-bounty-scope'
  authorizationAttestation: string
  authorizationConfirmed: true
  authorizationExpiresAt?: string
  selectedTeams: SecurityTeam[]
  targets: Array<{
    kind: 'website' | 'api' | 'repository' | 'cloud' | 'mobile' | 'network' | 'artifact' | 'media' | 'other'
    displayName: string
    locator: string
    environment: 'development' | 'staging' | 'production' | 'client' | 'unknown'
    notes?: string
  }>
}

export interface RunComparison {
  engagementId: string
  baselineRunId: string
  currentRunId: string
  counts: { introduced: number; persistent: number; resolved: number }
  introduced: Array<Record<string, unknown>>
  persistent: Array<Record<string, unknown>>
  resolved: Array<Record<string, unknown>>
  generatedAt: string
}

export interface PlatformData {
  workspace: {
    id: string
    slug: string
    name: string
    plan: string
    status: string
    safetyLevel: string
    killSwitchActive: boolean
  }
  user: { id: string; email: string; displayName: string; role: string }
  counts: Record<string, number>
  connectors: Array<{ id: string; name: string; status: string; version: string; capabilities: string[]; lastSeenAt: string | null }>
  agents: Array<{ id: string; name: string; kind: string; status: string; lastSeenAt: string }>
  tasks: PlatformTask[]
  approvals: PlatformApproval[]
  retention: { telemetryDays: number; taskDays: number; evidenceDays: number; auditDays: number; legalHoldDefault: boolean }
  ledger: { ok: boolean; entries: number; head: string; failedAt?: number }
  securityCoverage: SecurityCoverage
  shadowAI: ShadowAIData
}

export interface ReadinessGate {
  id: string
  label: string
  status: string
  owner: string
  closureItem: number | null
  verification: string[]
  evidence: string[]
}

export interface Program {
  name: string
  documentVersion: string
  verified: number
  total: number
  gates: ReadinessGate[]
  currentState: string
  rationale: string
  states: string[]
  marking: string
  allowExercise: boolean
  allowDiagnosticScore: boolean
  allowAssuranceStatement: boolean
}

export interface Gate {
  id: string
  name: string
  kind: string
  status: RunStatus
  lastRunId: string | null
  elapsedSeconds: number | null
}

export interface Team {
  id: string
  name: string
  color: string
  verb: string
  purpose: string
  status: RunStatus
  lastRunId: string | null
  passThreshold: number | null
  programWeight: number | null
  test: string
  automaticFailures: string[]
  components: Record<string, { name: string; weight: number }>
}

export interface GateRun {
  id: string
  gateId: string
  gateName: string
  mode: 'engineering' | 'assurance'
  status: RunStatus
  requestedAt: string
  startedAt: string | null
  finishedAt: string | null
  returnCode: number | null
  output: string
  elapsedSeconds: number | null
}

export interface AuditRecord {
  id: string
  at: string
  kind: string
  summary: string
  detail: Record<string, string>
  hash: string
  previous: string
  targetType?: string
  targetId?: string
}

export interface AgentSession {
  agent: string
  sessionId: string
  status: string
  task: string
  reason: string
  nextAction: string
  eventTime: string | null
}

export interface Snapshot {
  generatedAt: string
  deployment: {
    mode: 'operator' | 'demo' | 'saas'
    controlsEnabled: boolean
    streamingEnabled: boolean
    authentication: 'local-loopback' | 'public-read-only' | 'cloudflare-access' | 'development'
    dataClass: string
  }
  program: Program
  repo: {
    branch: string
    commit: string
    committedAt: string
    subject: string
    dirty: boolean
    changedCount: number
    changes: string[]
  }
  gates: {
    engineering: Gate[]
    engineeringCount: number
    assurance: Array<{ id: string; name: string; kind: string }>
  }
  teams: Team[]
  agents: {
    online: boolean
    demo?: boolean
    activeCount: number
    blockedCount: number
    securityTeamCount?: number
    sessions: AgentSession[]
    collisions?: Array<{ workspace: string; branch: string; reason: string; sessions: string[] }>
    ledger: { ok: boolean; checked?: number; entries?: number; head: string }
  }
  runs: GateRun[]
  activity: AuditRecord[]
  controlLedger: { ok: boolean; entries: number; head: string; failedAt?: number }
  platform?: PlatformData
}
