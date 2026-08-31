import {
  AlertTriangle,
  ArrowRight,
  Check,
  ClipboardCheck,
  Download,
  FileCheck2,
  FilePlus2,
  Fingerprint,
  GitCompareArrows,
  Globe2,
  LockKeyhole,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { SecurityTeam } from './types'

type DemoStage = 'scope' | 'intake' | 'run' | 'results'
type DemoSeverity = 'low' | 'medium' | 'high' | 'critical'

interface DemoFinding {
  title: string
  detail: string
  severity: DemoSeverity
  team: SecurityTeam
}

interface DemoAsset {
  id: string
  name: string
  mediaType: string
  sizeBytes: number
  source: 'sample' | 'browser-metadata'
}

interface DemoScenario {
  id: string
  label: string
  title: string
  detail: string
  target: string
  targetKind: string
  objective: string
  baselineScore: number
  remediatedScore: number
  sampleAssets: Omit<DemoAsset, 'id' | 'source'>[]
  findings: DemoFinding[]
  icon: typeof Globe2
}

const reviewTeams: Array<{ id: SecurityTeam; name: string; verb: string; output: string }> = [
  { id: 'purple', name: 'Purple', verb: 'Coordinate', output: 'Mapped scope to attack paths and validation coverage.' },
  { id: 'white', name: 'White', verb: 'Authorize', output: 'Verified authority, exclusions, stop conditions and evidence rules.' },
  { id: 'yellow', name: 'Yellow', verb: 'Build', output: 'Reviewed dependencies, configuration and secure delivery controls.' },
  { id: 'green', name: 'Green', verb: 'Engineer', output: 'Tested prevention, identity and detection design assumptions.' },
  { id: 'orange', name: 'Orange', verb: 'Anticipate', output: 'Modeled abuse cases, business impact and likely attacker choices.' },
  { id: 'blue', name: 'Blue', verb: 'Defend', output: 'Checked observability, response, recovery and containment readiness.' },
  { id: 'red', name: 'Red', verb: 'Prove', output: 'Validated the highest-risk claims with bounded synthetic evidence.' },
]

const scenarios: DemoScenario[] = [
  {
    id: 'prelaunch',
    label: 'PRE-LAUNCH',
    title: 'SaaS launch readiness',
    detail: 'Challenge a synthetic product before customers or production data arrive.',
    target: 'launch-preview.example',
    targetKind: 'Staging application + API',
    objective: 'Prove the release has a defensible identity boundary, recoverable data path, controlled AI use and client-ready evidence.',
    baselineScore: 64,
    remediatedScore: 91,
    icon: ClipboardCheck,
    sampleAssets: [
      { name: 'architecture-overview.pdf', mediaType: 'document', sizeBytes: 482_144 },
      { name: 'release-sbom.spdx.json', mediaType: 'structured data', sizeBytes: 128_420 },
      { name: 'openapi-staging.yaml', mediaType: 'API contract', sizeBytes: 74_118 },
    ],
    findings: [
      { title: 'Administrative route lacks a bounded retry policy', detail: 'The synthetic API contract exposes an administrative action without an explicit retry ceiling.', severity: 'high', team: 'green' },
      { title: 'Recovery evidence is older than the release candidate', detail: 'The latest restore receipt does not cover the build represented by this mission.', severity: 'high', team: 'blue' },
      { title: 'One transitive package is not version-pinned', detail: 'The sample SBOM records a floating development dependency.', severity: 'medium', team: 'yellow' },
    ],
  },
  {
    id: 'site',
    label: 'OWN SITE',
    title: 'External site defense review',
    detail: 'See how an owned public site becomes a bounded, repeatable assessment.',
    target: 'owned-storefront.example',
    targetKind: 'Authorized public website',
    objective: 'Find exploitable exposure without destructive testing, preserve evidence and turn each result into an owned remediation decision.',
    baselineScore: 71,
    remediatedScore: 94,
    icon: Globe2,
    sampleAssets: [
      { name: 'authorized-scope.txt', mediaType: 'scope record', sizeBytes: 8_214 },
      { name: 'site-headers.json', mediaType: 'structured data', sizeBytes: 18_904 },
      { name: 'recovery-runbook.pdf', mediaType: 'document', sizeBytes: 311_080 },
    ],
    findings: [
      { title: 'Session cookie policy is inconsistent across routes', detail: 'The synthetic header sample omits the same-site boundary on one application path.', severity: 'high', team: 'red' },
      { title: 'Origin monitoring does not cover certificate drift', detail: 'The sample telemetry plan records availability but no certificate-change signal.', severity: 'medium', team: 'blue' },
      { title: 'Recovery owner is not named in the runbook', detail: 'The evidence defines recovery steps without an accountable decision owner.', severity: 'medium', team: 'white' },
    ],
  },
  {
    id: 'shadow-ai',
    label: 'SHADOW AI',
    title: 'Unsanctioned AI exposure',
    detail: 'Correlate synthetic inventory signals without collecting prompt content.',
    target: 'sample-workspace.example',
    targetKind: 'Workforce AI inventory',
    objective: 'Discover unknown models, tools, agents and MCP connections; classify risk; and produce enforceable next actions without retaining prompts.',
    baselineScore: 58,
    remediatedScore: 88,
    icon: Sparkles,
    sampleAssets: [
      { name: 'gateway-ai-domains.csv', mediaType: 'gateway inventory', sizeBytes: 92_118 },
      { name: 'browser-extensions.json', mediaType: 'endpoint inventory', sizeBytes: 55_201 },
      { name: 'mcp-tool-registry.json', mediaType: 'agent inventory', sizeBytes: 43_889 },
    ],
    findings: [
      { title: 'Unknown AI extension can read restricted pages', detail: 'A synthetic browser inventory grants broad page access to an unapproved AI extension.', severity: 'critical', team: 'blue' },
      { title: 'Local agent exposes an unclassified MCP tool', detail: 'The example registry contains a write-capable tool without an owner or data classification.', severity: 'high', team: 'green' },
      { title: 'Vendor review is missing for one model endpoint', detail: 'The sample gateway signal identifies an endpoint outside the approved vendor list.', severity: 'medium', team: 'white' },
    ],
  },
  {
    id: 'client',
    label: 'CLIENT WORK',
    title: 'Authorized client assessment',
    detail: 'Keep scope, evidence, findings, remediation and reporting client-separated.',
    target: 'client-staging.example',
    targetKind: 'Client-authorized environment',
    objective: 'Translate a client request into a controlled work order, preserve chain of custody and return prioritized findings with proof.',
    baselineScore: 67,
    remediatedScore: 92,
    icon: Users,
    sampleAssets: [
      { name: 'signed-authorization.pdf', mediaType: 'authority record', sizeBytes: 218_309 },
      { name: 'client-architecture.png', mediaType: 'image', sizeBytes: 824_117 },
      { name: 'sanitized-app-log.ndjson', mediaType: 'log data', sizeBytes: 1_208_422 },
    ],
    findings: [
      { title: 'Authorization expiry is not connected to the stop control', detail: 'The synthetic work order records an expiry without an automatic execution hold.', severity: 'high', team: 'white' },
      { title: 'Sensitive log fields are not consistently redacted', detail: 'The example log schema leaves one customer identifier outside the redaction rule.', severity: 'high', team: 'yellow' },
      { title: 'Finding ownership is missing from the delivery contract', detail: 'The sample statement of work defines severity but not remediation ownership.', severity: 'medium', team: 'purple' },
    ],
  },
]

const stageLabels: Array<{ id: DemoStage; label: string; detail: string }> = [
  { id: 'scope', label: 'Choose mission', detail: 'Safe synthetic scope' },
  { id: 'intake', label: 'Add inputs', detail: 'Samples or local metadata' },
  { id: 'run', label: 'Process', detail: 'Seven-team simulation' },
  { id: 'results', label: 'Use outputs', detail: 'Findings, compare, export' },
]

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 ** 2).toFixed(1)} MB`
}

function payloadUrl(payload: unknown): string {
  return `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(payload, null, 2))}`
}

function markdownUrl(value: string): string {
  return `data:text/markdown;charset=utf-8,${encodeURIComponent(value)}`
}

export function ShowcaseQuickstart({ onStart }: { onStart: () => void }) {
  return (
    <section className="demo-quickstart" aria-labelledby="demo-quickstart-title">
      <div className="demo-quickstart__intro">
        <span><Play size={12} fill="currentColor" /> INTERACTIVE PUBLIC MISSION</span>
        <h2 id="demo-quickstart-title">Do the work. Don’t just tour the screens.</h2>
        <p>Choose a safe scenario, add sample or browser-only input metadata, watch seven teams process it, then compare and export the proof package.</p>
      </div>
      <ol>
        <li><strong>01</strong><span>Scope<small>Choose a mission</small></span></li>
        <li><strong>02</strong><span>Intake<small>Add inputs</small></span></li>
        <li><strong>03</strong><span>Process<small>Run seven teams</small></span></li>
        <li><strong>04</strong><span>Prove<small>Compare + export</small></span></li>
      </ol>
      <button type="button" className="button button--primary" onClick={onStart}>Open mission simulator <ArrowRight size={15} /></button>
      <small><LockKeyhole size={11} /> Browser-contained simulation. No real target is contacted and no file content is uploaded.</small>
    </section>
  )
}

export default function ShowcaseMission() {
  const [scenarioId, setScenarioId] = useState(scenarios[0].id)
  const [stage, setStage] = useState<DemoStage>('scope')
  const [assets, setAssets] = useState<DemoAsset[]>([])
  const [activeTeam, setActiveTeam] = useState(0)
  const [runNumber, setRunNumber] = useState(0)
  const scenario = scenarios.find((item) => item.id === scenarioId) ?? scenarios[0]
  const stageIndex = stageLabels.findIndex((item) => item.id === stage)

  useEffect(() => {
    if (stage !== 'run') return
    const timer = window.setTimeout(() => {
      if (activeTeam < reviewTeams.length) {
        setActiveTeam((current) => current + 1)
      } else {
        setStage('results')
      }
    }, activeTeam < reviewTeams.length ? 260 : 360)
    return () => window.clearTimeout(timer)
  }, [activeTeam, stage])

  const selectScenario = (id: string) => {
    setScenarioId(id)
    setAssets([])
    setRunNumber(0)
    setActiveTeam(0)
    setStage('scope')
  }

  const addSampleAssets = () => {
    const samples = scenario.sampleAssets.map((asset, index) => ({ ...asset, id: `sample-${scenario.id}-${index}`, source: 'sample' as const }))
    setAssets((current) => [...current, ...samples.filter((sample) => !current.some((asset) => asset.id === sample.id))])
  }

  const addBrowserFiles = (files: File[]) => {
    if (files.length === 0) return
    setAssets((current) => [
      ...current,
      ...files.map((file, index) => ({
        id: `browser-${Date.now()}-${index}`,
        name: file.name,
        mediaType: file.type || 'unclassified local file',
        sizeBytes: file.size,
        source: 'browser-metadata' as const,
      })),
    ])
  }

  const beginRun = () => {
    setRunNumber((current) => current + 1)
    setActiveTeam(0)
    setStage('run')
  }

  const reset = () => {
    setStage('scope')
    setAssets([])
    setActiveTeam(0)
    setRunNumber(0)
  }

  const currentFindings = useMemo(() => scenario.findings.map((finding, index) => ({
    ...finding,
    status: runNumber >= 2 && index < 2 ? 'resolved' : 'open',
  })), [runNumber, scenario])
  const score = runNumber >= 2 ? scenario.remediatedScore : scenario.baselineScore
  const exportPayload = {
    classification: 'PUBLIC_SYNTHETIC_DEMONSTRATION',
    generatedAt: new Date().toISOString(),
    product: 'AEGIS Mission Control',
    boundary: {
      realTargetContacted: false,
      fileContentUploaded: false,
      serverMutationPerformed: false,
      note: 'This package demonstrates the workflow. It is not a real security assessment.',
    },
    engagement: {
      scenario: scenario.title,
      target: scenario.target,
      targetKind: scenario.targetKind,
      objective: scenario.objective,
      authority: 'Pre-authorized synthetic public demonstration',
    },
    inputs: assets.map(({ id: _id, ...asset }) => asset),
    teams: reviewTeams,
    run: { sequence: runNumber, score, status: 'completed' },
    findings: currentFindings,
    comparison: runNumber >= 2 ? { resolved: 2, persistent: 1, introduced: 0, scoreChange: scenario.remediatedScore - scenario.baselineScore } : null,
  }
  const markdown = [
    '# AEGIS Synthetic Mission Report',
    '',
    '> PUBLIC SYNTHETIC DEMONSTRATION — no real target contacted and no file content uploaded.',
    '',
    `## ${scenario.title}`,
    '',
    `- Target: ${scenario.target} (${scenario.targetKind})`,
    `- Run: #${runNumber}`,
    `- Score: ${score}/100`,
    `- Inputs: ${assets.length}`,
    '',
    '## Findings',
    '',
    ...currentFindings.map((finding) => `- **${finding.severity.toUpperCase()} / ${finding.status.toUpperCase()} / ${finding.team.toUpperCase()}** — ${finding.title}: ${finding.detail}`),
    '',
    'Generated by the browser-contained AEGIS public workflow demonstration.',
  ].join('\n')

  return (
    <div className="view showcase-mission">
      <section className="showcase-mission__mast">
        <div>
          <span className="eyebrow"><Sparkles size={13} /> PUBLIC / SAFE / INTERACTIVE</span>
          <h1 data-view-heading tabIndex={-1}>Run a mission.<br /><em>See what AEGIS produces.</em></h1>
          <p>This is a real interactive product walkthrough using synthetic targets. It demonstrates the operating path without touching a website, sending file content, or changing the private control plane.</p>
        </div>
        <div className="showcase-boundary">
          <LockKeyhole size={18} />
          <div><strong>DEMO SAFETY BOUNDARY</strong><span>Browser-contained state</span><span>Zero real target traffic</span><span>Zero file-content upload</span></div>
        </div>
      </section>

      <ol className="showcase-stage-rail" aria-label="Interactive mission steps">
        {stageLabels.map((item, index) => (
          <li key={item.id} className={index < stageIndex ? 'is-complete' : index === stageIndex ? 'is-current' : ''} aria-current={index === stageIndex ? 'step' : undefined}>
            <span>{index < stageIndex ? <Check size={13} /> : String(index + 1).padStart(2, '0')}</span>
            <div><strong>{item.label}</strong><small>{item.detail}</small></div>
          </li>
        ))}
      </ol>

      {stage === 'scope' && (
        <section className="showcase-workspace" aria-labelledby="mission-scope-title">
          <header><span>STEP 01 / SCOPE</span><h2 id="mission-scope-title">What do you need the security teams to do?</h2><p>Pick the closest use case. Every option uses a reserved <code>.example</code> target and synthetic evidence.</p></header>
          <div className="showcase-scenarios">
            {scenarios.map((item) => {
              const Icon = item.icon
              const selected = item.id === scenario.id
              return (
                <button type="button" key={item.id} className={selected ? 'is-selected' : ''} onClick={() => selectScenario(item.id)} aria-pressed={selected}>
                  <span><Icon size={18} /><small>{item.label}</small></span>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  <em>{selected ? 'SELECTED' : 'CHOOSE MISSION'}</em>
                </button>
              )
            })}
          </div>
          <div className="showcase-scope-contract">
            <div><span>SYNTHETIC TARGET</span><strong>{scenario.target}</strong><small>{scenario.targetKind}</small></div>
            <div><span>MISSION OBJECTIVE</span><p>{scenario.objective}</p></div>
            <div><span>AUTHORITY</span><strong><ShieldCheck size={15} /> Pre-authorized demonstration</strong><small>Non-destructive simulation only</small></div>
          </div>
          <footer><span><LockKeyhole size={13} /> Real targets cannot be entered in the public showcase.</span><button type="button" className="button button--primary" onClick={() => setStage('intake')}>Continue to safe intake <ArrowRight size={15} /></button></footer>
        </section>
      )}

      {stage === 'intake' && (
        <section className="showcase-workspace" aria-labelledby="mission-intake-title">
          <header><span>STEP 02 / INTAKE</span><h2 id="mission-intake-title">Give the teams enough context to work.</h2><p>Add prepared sample inputs, or choose local files to demonstrate intake. Local file content is never read or sent; only the visible name, type and size are held in this browser tab.</p></header>
          <div className="showcase-intake-grid">
            <div className="showcase-input-actions">
              <button type="button" className="showcase-sample-button" onClick={addSampleAssets}><FilePlus2 size={22} /><span><strong>Add prepared sample inputs</strong><small>{scenario.sampleAssets.map((asset) => asset.name).join(' · ')}</small></span><ArrowRight size={16} /></button>
              <label className="showcase-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); addBrowserFiles(Array.from(event.dataTransfer.files)) }}>
                <input type="file" multiple onChange={(event) => { addBrowserFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} />
                <Upload size={22} />
                <strong>Drop files or choose from this device</strong>
                <span>Documents · images · audio · video · logs · JSON/CSV · archives</span>
                <small>BROWSER METADATA ONLY / CONTENT NEVER LEAVES DEVICE</small>
              </label>
            </div>
            <div className="showcase-input-register">
              <div><span>INPUT REGISTER</span><strong>{assets.length} attached</strong>{assets.length > 0 && <button type="button" onClick={() => setAssets([])}>Clear</button>}</div>
              {assets.length === 0 ? <div className="showcase-input-empty"><FileCheck2 size={23} /><strong>No inputs yet</strong><span>Add the prepared set for the fastest walkthrough.</span></div> : assets.map((asset) => <article key={asset.id}><FileCheck2 size={15} /><div><strong>{asset.name}</strong><span>{asset.mediaType} · {formatBytes(asset.sizeBytes)}</span></div><em>{asset.source === 'sample' ? 'SYNTHETIC' : 'METADATA ONLY'}</em></article>)}
            </div>
          </div>
          <footer><button type="button" className="button button--quiet" onClick={() => setStage('scope')}>Back to scope</button><button type="button" className="button button--primary" disabled={assets.length === 0} onClick={beginRun}><Play size={15} fill="currentColor" /> Begin seven-team simulation</button></footer>
        </section>
      )}

      {stage === 'run' && (
        <section className="showcase-workspace showcase-processing" aria-labelledby="mission-run-title" aria-live="polite">
          <header><span>STEP 03 / PROCESSING</span><h2 id="mission-run-title">Seven teams are processing the mission.</h2><p>Each function contributes a distinct decision. The public simulator generates deterministic sample results; a customer workspace would bind these stages to authorized connectors, approvals and evidence.</p></header>
          <div className="showcase-progress" role="progressbar" aria-label="Seven-team mission progress" aria-valuemin={0} aria-valuemax={reviewTeams.length} aria-valuenow={Math.min(activeTeam, reviewTeams.length)}><i style={{ width: `${Math.min(100, (activeTeam / reviewTeams.length) * 100)}%` }} /></div>
          <div className="showcase-team-run">
            {reviewTeams.map((team, index) => {
              const complete = index < activeTeam
              const active = index === activeTeam
              return <article key={team.id} className={`${complete ? 'is-complete' : ''} ${active ? 'is-active' : ''} team-${team.id}`}><span>{complete ? <Check size={14} /> : String(index + 1).padStart(2, '0')}</span><div><small>{team.verb.toUpperCase()}</small><strong>{team.name} Team</strong><p>{complete ? team.output : active ? 'Processing synthetic inputs…' : 'Waiting for upstream decision'}</p></div><em>{complete ? 'COMPLETE' : active ? 'ACTIVE' : 'QUEUED'}</em></article>
            })}
          </div>
          <div className="showcase-processing-note"><Fingerprint size={16} /><span><strong>Evidence ledger simulation active</strong> — team decisions are being assembled into one synthetic, exportable run record.</span></div>
        </section>
      )}

      {stage === 'results' && (
        <section className="showcase-workspace" aria-labelledby="mission-results-title">
          <header><span>STEP 04 / OUTPUTS</span><h2 id="mission-results-title">Mission results are ready to use.</h2><p>AEGIS turns team activity into a prioritized decision package: what was checked, what failed, who owns it, what changed and what can be exported.</p></header>
          <div className="showcase-result-hero">
            <div className="showcase-score"><span>MISSION SCORE</span><strong>{score}<small>/100</small></strong><em>{runNumber >= 2 ? 'REMEDIATION VERIFIED' : 'ACTION REQUIRED'}</em></div>
            <div className="showcase-result-summary"><span>RUN #{String(runNumber).padStart(2, '0')} / {scenario.label}</span><h3>{runNumber >= 2 ? 'The sample fixes materially reduced exposure.' : 'Three findings need an owner before release.'}</h3><p>{runNumber >= 2 ? 'Two findings resolved, one remains visible, and no new exposure was introduced.' : 'Severity is not averaged away. Every open high or critical result remains explicit in the decision package.'}</p></div>
            <div className="showcase-result-seal"><ShieldCheck size={23} /><strong>CHAIN ASSEMBLED</strong><span>{reviewTeams.length} team decisions</span><span>{assets.length} input records</span><span>{currentFindings.length} findings</span></div>
          </div>
          {runNumber >= 2 && <div className="showcase-comparison" aria-label="Run comparison"><span><strong>0</strong><small>Introduced</small></span><span><strong>1</strong><small>Persistent</small></span><span className="is-resolved"><strong>2</strong><small>Resolved</small></span><span className="is-score"><strong>+{scenario.remediatedScore - scenario.baselineScore}</strong><small>Score change</small></span></div>}
          <div className="showcase-result-grid">
            <div className="showcase-findings">
              <div><span>PRIORITIZED FINDINGS</span><strong>{currentFindings.filter((finding) => finding.status === 'open').length} open</strong></div>
              {currentFindings.map((finding) => <article key={finding.title} className={`severity-${finding.severity} is-${finding.status}`}><i /><div><span>{finding.team.toUpperCase()} TEAM / {finding.severity.toUpperCase()}</span><strong>{finding.title}</strong><p>{finding.detail}</p></div><em>{finding.status.toUpperCase()}</em></article>)}
            </div>
            <div className="showcase-deliverables">
              <span>WHAT YOU CAN DO NEXT</span>
              <article><ClipboardCheck size={18} /><div><strong>Assign remediation</strong><p>Turn findings into owned work with severity, evidence and acceptance criteria.</p></div></article>
              <article><GitCompareArrows size={18} /><div><strong>Rerun and compare</strong><p>Prove which findings resolved, persisted or appeared after a change.</p></div></article>
              <article><Download size={18} /><div><strong>Export the record</strong><p>Save a client-ready package for delivery, audit or later comparison.</p></div></article>
            </div>
          </div>
          <footer className="showcase-result-actions">
            <button type="button" className="button button--quiet" onClick={reset}><RefreshCw size={15} /> Start another mission</button>
            {runNumber < 2 && <button type="button" className="button button--primary" onClick={beginRun}><GitCompareArrows size={15} /> Apply sample fixes + rerun</button>}
            <a className="button button--quiet" href={payloadUrl(exportPayload)} download={`aegis-${scenario.id}-synthetic-evidence.json`}><Download size={15} /> Export evidence JSON</a>
            <a className="button button--quiet" href={markdownUrl(markdown)} download={`aegis-${scenario.id}-synthetic-report.md`}><Download size={15} /> Export report</a>
          </footer>
          <div className="showcase-disclaimer"><AlertTriangle size={14} /><span><strong>Demonstration boundary:</strong> this output is synthetic and is not an assessment of any real system. Real work runs only in an isolated, authenticated customer workspace with recorded authority and governed connectors.</span></div>
        </section>
      )}
    </div>
  )
}
