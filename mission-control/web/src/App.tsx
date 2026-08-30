import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  Ban,
  BookOpen,
  Check,
  ChevronRight,
  CircleStop,
  Clock3,
  ClipboardCheck,
  Command,
  FileCheck2,
  Download,
  FolderOpen,
  Fingerprint,
  GitBranch,
  GitCompareArrows,
  Globe2,
  Layers3,
  LayoutDashboard,
  LockKeyhole,
  Maximize2,
  Minus,
  Monitor,
  Network,
  Play,
  Plus,
  Radio,
  RotateCcw,
  ScanSearch,
  Sparkles,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  SlidersHorizontal,
  TerminalSquare,
  Target,
  Upload,
  Users,
  X,
  Zap,
} from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import { useMissionControl } from './api'
import type { AuditRecord, Engagement, EngagementCreateInput, GateRun, ReadinessGate, RetentionInput, RunComparison, SafetyLevel, SecurityControl, SecurityTeam, ShadowAIData, ShadowAIPolicyInput, Snapshot, Team } from './types'

type View = 'overview' | 'engagements' | 'coverage' | 'shadow' | 'teams' | 'gates' | 'agents' | 'workspace' | 'evidence'
type ViewScale = 80 | 90 | 100 | 110 | 120
type ViewDensity = 'comfortable' | 'compact'

const viewScales: ViewScale[] = [80, 90, 100, 110, 120]
const guideVersion = '2026.08.30.1'

const nav: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: 'Command', icon: LayoutDashboard },
  { id: 'engagements', label: 'Engagements', icon: Target },
  { id: 'coverage', label: 'Security coverage', icon: ScanSearch },
  { id: 'shadow', label: 'Shadow AI defense', icon: ShieldAlert },
  { id: 'teams', label: 'Seven teams', icon: Users },
  { id: 'gates', label: 'Gate runner', icon: ShieldCheck },
  { id: 'agents', label: 'Live agents', icon: Bot },
  { id: 'workspace', label: 'Workspace controls', icon: SlidersHorizontal },
  { id: 'evidence', label: 'Evidence', icon: FileCheck2 },
]

const viewHash: Record<View, string> = {
  overview: '#/command',
  engagements: '#/engagements',
  coverage: '#/security-coverage',
  shadow: '#/shadow-ai',
  teams: '#/seven-teams',
  gates: '#/gate-runner',
  agents: '#/live-agents',
  workspace: '#/workspace-controls',
  evidence: '#/evidence',
}

function viewFromLocation(): View {
  const entry = (Object.entries(viewHash) as Array<[View, string]>).find(([, hash]) => hash === window.location.hash)
  return entry?.[0] ?? 'overview'
}

function words(value: string): string {
  return value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase())
}

function shortTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function elapsed(value: number | null | undefined): string {
  if (value == null) return '—'
  return value >= 60 ? `${Math.floor(value / 60)}m ${Math.round(value % 60)}s` : `${value.toFixed(1)}s`
}

function bytes(value: number): string {
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`
  return `${(value / 1024 ** 3).toFixed(1)} GB`
}

function moneyFromMicrousd(value: number): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value / 1_000_000)
}

function statusText(status: string): string {
  return status === 'not_run' ? 'Standing by' : words(status)
}

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="AEGIS Mission Control">
      <div className="brand__mark" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
        <b>A</b>
      </div>
      {!compact && (
        <div className="brand__type">
          <strong>AEGIS</strong>
          <small>Mission Control</small>
        </div>
      )}
    </div>
  )
}

function StatusDot({ online, label }: { online: boolean; label: string }) {
  return (
    <span className={`status-dot ${online ? 'is-online' : 'is-offline'}`}>
      <i />
      {label}
    </span>
  )
}

function NavRail({ view, setView }: { view: View; setView: (view: View) => void }) {
  return (
    <aside className="nav-rail">
      <Logo compact />
      <nav aria-label="Mission Control views">
        {nav.map((item) => {
          const Icon = item.icon
          return (
            <button
              type="button"
              key={item.id}
              className={view === item.id ? 'is-active' : ''}
              onClick={() => setView(item.id)}
              aria-label={item.label}
              aria-current={view === item.id ? 'page' : undefined}
              data-tooltip={item.label}
            >
              <Icon size={19} strokeWidth={1.7} />
            </button>
          )
        })}
      </nav>
      <div className="rail-spectrum" aria-label="Seven team spectrum">
        {['purple', 'white', 'yellow', 'green', 'orange', 'blue', 'red'].map((team) => (
          <i key={team} className={`team-${team}`} />
        ))}
      </div>
      <div className="rail-avatar" aria-label="Local operator identity">RB</div>
    </aside>
  )
}

function TopBar({
  snapshot,
  connected,
  onCommand,
  onGuide,
  onViewSettings,
  viewScale,
}: {
  snapshot: Snapshot
  connected: boolean
  onCommand: () => void
  onGuide: () => void
  onViewSettings: () => void
  viewScale: ViewScale
}) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  return (
    <header className="topbar">
      <Logo />
      <div className="topbar__center">
        <span className="eyebrow">CONTROL PLANE / {snapshot.deployment.mode.toUpperCase()}</span>
        <strong>{words(snapshot.program.currentState)}</strong>
      </div>
      <div className="topbar__right">
        <StatusDot
          online={connected}
          label={connected ? (snapshot.deployment.mode === 'demo' ? 'Demo feed' : snapshot.deployment.mode === 'saas' ? 'Tenant uplink' : 'Live uplink') : 'Reconnecting'}
        />
        <button type="button" className="utility-trigger" onClick={onGuide} aria-label="Open the Mission Control guide">
          <BookOpen size={14} />
          <span>Guide</span>
          <kbd>?</kbd>
        </button>
        <button type="button" className="utility-trigger view-trigger" onClick={onViewSettings} aria-label={`Adjust view size, currently ${viewScale}%`}>
          <Monitor size={14} />
          <span>{viewScale}%</span>
        </button>
        <button type="button" className="command-trigger" onClick={onCommand}>
          <Command size={15} />
          Command
          <kbd>⌘ K</kbd>
        </button>
        <div className="clock">
          <strong>{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          <small>{now.toLocaleDateString([], { month: 'short', day: '2-digit' }).toUpperCase()}</small>
        </div>
      </div>
    </header>
  )
}

function MarkingBar({ snapshot }: { snapshot: Snapshot }) {
  const demo = snapshot.deployment.mode === 'demo'
  const saas = snapshot.deployment.mode === 'saas'
  return (
    <aside className={`marking-bar ${demo ? 'is-demo' : ''}`} aria-label="Data safety classification">
      {demo ? <Radio size={13} /> : <LockKeyhole size={13} />}
      <span>{demo ? 'PUBLIC_READ_ONLY_SHOWCASE' : saas ? 'TENANT_ISOLATED_WORKSPACE' : snapshot.program.marking}</span>
      <i />
      <span>{demo ? 'SYNTHETIC AGENT FEED' : saas ? 'CUSTOMER DATA BOUNDARY ACTIVE' : 'ASSURANCE OUTPUT LOCKED'}</span>
      <i />
      <span>{demo ? 'CONTROL ACTIONS REMOVED' : saas ? 'RAW AI PROMPTS NOT RETAINED' : 'DIAGNOSTIC OPERATIONS PERMITTED'}</span>
    </aside>
  )
}

function TrustCore({ program }: { program: Snapshot['program'] }) {
  const progress = program.total ? program.verified / program.total : 0
  const radius = 84
  const circumference = 2 * Math.PI * radius
  const style = { '--trust-progress': `${Math.round(progress * 100)}%` } as CSSProperties
  return (
    <div className="trust-core" style={style}>
      <div className="trust-core__radar" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </div>
      <svg viewBox="0 0 210 210" aria-label={`${program.verified} of ${program.total} readiness gates verified`}>
        <circle className="trust-core__track" cx="105" cy="105" r={radius} />
        <circle
          className="trust-core__progress"
          cx="105"
          cy="105"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
        />
      </svg>
      <div className="trust-core__number">
        <span>READINESS</span>
        <strong>{program.verified}<small>/{program.total}</small></strong>
        <em>GATES VERIFIED</em>
      </div>
      <div className="trust-core__orbit" aria-hidden="true">
        <i className="team-purple" />
        <i className="team-white" />
        <i className="team-yellow" />
        <i className="team-green" />
        <i className="team-orange" />
        <i className="team-blue" />
        <i className="team-red" />
      </div>
    </div>
  )
}

function Lifecycle({ program }: { program: Snapshot['program'] }) {
  const activeIndex = Math.max(0, program.states.indexOf(program.currentState))
  return (
    <div className="lifecycle" aria-label="Program lifecycle">
      {program.states.map((state, index) => (
        <div
          key={state}
          className={`lifecycle__step ${index < activeIndex ? 'is-complete' : ''} ${index === activeIndex ? 'is-current' : ''}`}
        >
          <span>{String(index + 1).padStart(2, '0')}</span>
          <i>{index < activeIndex ? <Check size={12} /> : null}</i>
          <strong>{words(state)}</strong>
        </div>
      ))}
    </div>
  )
}

function ReadinessItem({ gate }: { gate: ReadinessGate }) {
  const verified = gate.status === 'VERIFIED'
  return (
    <details className={`readiness-item ${verified ? 'is-verified' : 'is-pending'}`}>
      <summary>
        <span className="readiness-item__icon">{verified ? <Check size={14} /> : <Clock3 size={14} />}</span>
        <span>
          <strong>{gate.label}</strong>
          <small>{gate.owner}</small>
        </span>
        <em>{gate.status}</em>
        <ChevronRight size={15} />
      </summary>
      <div className="readiness-item__detail">
        <span>Verification contract</span>
        <ul>
          {gate.verification.slice(0, 3).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
    </details>
  )
}

function TeamCard({ team, onRun, busy, expanded = false }: { team: Team; onRun: (id: string) => void; busy: boolean; expanded?: boolean }) {
  const style = { '--team': team.color } as CSSProperties
  return (
    <article className={`team-card ${expanded ? 'team-card--expanded' : ''}`} style={style}>
      <div className="team-card__signal"><span /><span /><span /></div>
      <header>
        <div className="team-card__monogram">{team.id.slice(0, 2).toUpperCase()}</div>
        <div>
          <span>{team.verb}</span>
          {expanded ? <h2>{team.name}</h2> : <h3>{team.name}</h3>}
        </div>
        <em className={`run-status is-${team.status}`}>{statusText(team.status)}</em>
      </header>
      <p>{team.purpose}</p>
      {expanded && <p className="team-card__test">{team.test}</p>}
      <footer>
        <div>
          <span>PASS FLOOR</span>
          <strong>{team.passThreshold ? `${Math.round(team.passThreshold * 100)}%` : '—'}</strong>
        </div>
        <div>
          <span>PROGRAM WEIGHT</span>
          <strong>{team.programWeight ? `${(team.programWeight * 100).toFixed(2)}%` : '—'}</strong>
        </div>
        <button type="button" onClick={() => onRun(team.id)} disabled={busy} aria-label={`Run ${team.name} gate`}>
          {team.status === 'running' ? <RefreshCw className="spin" size={14} /> : <Play size={14} fill="currentColor" />}
          Run gate
        </button>
      </footer>
      {expanded && team.automaticFailures.length > 0 && (
        <div className="auto-fail">
          <AlertTriangle size={14} />
          <div><span>AUTOMATIC FAILURE</span><strong>{team.automaticFailures[0]}</strong></div>
        </div>
      )}
    </article>
  )
}

function RunBadge({ status }: { status: string }) {
  return <span className={`run-badge is-${status}`}><i />{statusText(status)}</span>
}

function ActivityFeed({ activity, runs }: { activity: AuditRecord[]; runs: GateRun[] }) {
  const rows = activity.length ? activity : runs.map((run) => ({
    id: run.id,
    at: run.requestedAt,
    kind: `run.${run.status}`,
    summary: `${run.gateName}: ${run.status}`,
    detail: {},
    hash: run.id,
    previous: '',
  }))
  return (
    <div className="activity-feed">
      <div className="panel-heading">
        <div><span>LIVE CONTROL LOG</span><h2>Watchfloor activity</h2></div>
        <Radio size={16} />
      </div>
      <div className="activity-feed__rows">
        {rows.slice(0, 6).map((item, index) => (
          <div className="activity-row" key={item.id} style={{ animationDelay: `${index * 50}ms` }}>
            <i className={item.kind.includes('completed') ? 'is-complete' : ''} />
            <div>
              <strong>{item.summary}</strong>
              <small>{words(item.kind)} · {shortTime(item.at)}</small>
            </div>
          </div>
        ))}
        {rows.length === 0 && (
          <div className="empty-row"><Radio size={18} /><span>Control plane listening<br /><small>No operator actions recorded yet</small></span></div>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint: string; icon: ReactNode }) {
  return (
    <div className="stat">
      <div className="stat__icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  )
}

function SectionHeading({ overline, title, detail, action, nested = false }: { overline: string; title: string; detail: string; action?: ReactNode; nested?: boolean }) {
  return (
    <div className="section-heading">
      <div><span>{overline}</span>{nested ? <h2>{title}</h2> : <h1 data-view-heading tabIndex={-1}>{title}</h1>}<p>{detail}</p></div>
      {action}
    </div>
  )
}

function Overview({ snapshot, runGate, setView, busy, controlsEnabled }: { snapshot: Snapshot; runGate: (id: string) => void; setView: (view: View) => void; busy: boolean; controlsEnabled: boolean }) {
  const program = snapshot.program
  const pending = program.gates.filter((gate) => gate.status !== 'VERIFIED').length
  return (
    <div className="view view--overview">
      <section className="brief">
        <div className="brief__copy">
          <span className="eyebrow"><Zap size={12} fill="currentColor" /> COMMAND BRIEF / {snapshot.generatedAt.slice(0, 10)}</span>
          <h1 data-view-heading tabIndex={-1}>Trust is a state.<br /><em>Prove every transition.</em></h1>
          <p>{program.rationale}</p>
          <div className="brief__actions">
            <button type="button" className="button button--primary" onClick={() => setView('gates')}>
              Open gate runner <ArrowUpRight size={15} />
            </button>
            <button type="button" className="button button--quiet" onClick={() => setView('evidence')}>
              Inspect evidence
            </button>
          </div>
        </div>
        <div className="brief__core"><TrustCore program={program} /></div>
        <div className="assurance-lock">
          <div className="assurance-lock__top"><LockKeyhole size={18} /><span>ASSURANCE INTERLOCK</span></div>
          <strong>{program.allowAssuranceStatement ? 'RELEASED' : 'ENGAGED'}</strong>
          <p>{program.allowAssuranceStatement ? 'Program evidence permits an assurance statement.' : 'No assurance statement may leave this control plane.'}</p>
          <div className="assurance-lock__rule"><i /><span>{pending} human-controlled prerequisite{pending === 1 ? '' : 's'} remain</span></div>
          <small>FAIL-CLOSED // POLICY ENFORCED</small>
        </div>
      </section>

      <section className="stats-grid">
        <Stat label="READINESS" value={`${program.verified}/${program.total}`} hint={`${pending} prerequisite gates pending`} icon={<Fingerprint size={19} />} />
        <Stat label="ENGINEERING GATES" value={snapshot.gates.engineeringCount} hint="Executable from this console" icon={<Layers3 size={19} />} />
        <Stat label="ACTIVE AGENTS" value={snapshot.agents.activeCount} hint={`${snapshot.agents.securityTeamCount ?? 0} attached to this program`} icon={<Bot size={19} />} />
        <Stat label="WORKTREE" value={snapshot.repo.dirty ? snapshot.repo.changedCount : 'CLEAN'} hint={`${snapshot.repo.branch} @ ${snapshot.repo.commit}`} icon={<GitBranch size={19} />} />
      </section>

      <section className="trust-grid">
        <div className="panel lifecycle-panel">
          <div className="panel-heading">
              <div><span>TRUST SPINE</span><h2>Program state machine</h2></div>
            <div className="state-chip"><i />{words(program.currentState)}</div>
          </div>
          <Lifecycle program={program} />
        </div>
        <div className="panel readiness-panel">
          <div className="panel-heading">
            <div><span>HARD PREREQUISITES</span><h2>Readiness contract</h2></div>
            <span className="counter">{program.verified}/{program.total}</span>
          </div>
          <div className="readiness-list">
            {program.gates.map((gate) => <ReadinessItem gate={gate} key={gate.id} />)}
          </div>
        </div>
        <div className="panel activity-panel"><ActivityFeed activity={snapshot.activity} runs={snapshot.runs} /></div>
      </section>

      <section className="team-section">
        <SectionHeading
          nested
          overline="SEVEN FUNCTIONS / ONE OPERATING MODEL"
          title="The security spectrum"
          detail="Each team owns a distinct decision boundary. No score can average away an automatic failure."
          action={<button type="button" className="text-action" onClick={() => setView('teams')}>Full team matrix <ChevronRight size={15} /></button>}
        />
        <div className="team-grid">
          {snapshot.teams.map((team) => <TeamCard team={team} onRun={runGate} busy={busy || !controlsEnabled} key={team.id} />)}
        </div>
      </section>
    </div>
  )
}

function TeamsView({ snapshot, runGate, busy, controlsEnabled }: { snapshot: Snapshot; runGate: (id: string) => void; busy: boolean; controlsEnabled: boolean }) {
  return (
    <div className="view">
      <SectionHeading overline="OPERATING MODEL" title="Seven teams. Explicit boundaries." detail="Run a team's engineering contract or inspect the condition that immediately fails its score." />
      <div className="team-grid team-grid--expanded">
        {snapshot.teams.map((team) => <TeamCard team={team} onRun={runGate} busy={busy || !controlsEnabled} expanded key={team.id} />)}
      </div>
    </div>
  )
}

function GatesView({ snapshot, runGate, busy, onAssurance, controlsEnabled }: { snapshot: Snapshot; runGate: (id: string) => void; busy: boolean; onAssurance: () => void; controlsEnabled: boolean }) {
  const [selected, setSelected] = useState(snapshot.runs[0]?.id ?? '')
  const active = snapshot.runs.find((run) => run.id === selected) ?? snapshot.runs[0]
  useEffect(() => {
    if (snapshot.runs[0]?.status === 'running') setSelected(snapshot.runs[0].id)
  }, [snapshot.runs])
  return (
    <div className="view gate-view">
      <SectionHeading
        overline="EXECUTABLE CONTROL PLANE"
        title="Engineering gate runner"
        detail={controlsEnabled ? 'Commands are derived from ci_gates.json. Arbitrary shell execution is not exposed.' : 'Public showcase mode is read-only. Operator controls are removed at the server boundary.'}
        action={
          <div className="heading-actions">
            <button type="button" className="button button--quiet button--danger" onClick={onAssurance} disabled={busy || !controlsEnabled}><LockKeyhole size={15} /> Readiness check</button>
            {controlsEnabled
              ? <button type="button" className="button button--primary" onClick={() => runGate('all')} disabled={busy}>{busy ? <RefreshCw className="spin" size={15} /> : <Play size={15} fill="currentColor" />} Run all gates</button>
              : <span className="button button--status" role="status" aria-label="Control actions are unavailable in this public showcase"><LockKeyhole size={15} /> Read-only demo</span>}
          </div>
        }
      />
      <div className="gate-layout">
        <section className="panel gate-list-panel">
          <div className="panel-heading">
            <div><span>MANIFEST / {snapshot.gates.engineeringCount} GATES</span><h2>Verification matrix</h2></div>
            <StatusDot online={!busy && controlsEnabled} label={!controlsEnabled ? 'Runner locked' : (busy ? 'Runner occupied' : 'Runner ready')} />
          </div>
          <div className="gate-table" role="list" aria-label="Engineering verification gates">
            {snapshot.gates.engineering.map((gate, index) => (
              <div className="gate-row" role="listitem" key={gate.id}>
                <span className="gate-row__index">{String(index + 1).padStart(2, '0')}</span>
                <div className="gate-row__name"><strong>{gate.name}</strong><small>{gate.id} · {gate.kind}</small></div>
                <RunBadge status={gate.status} />
                <span className="gate-row__time">{elapsed(gate.elapsedSeconds)}</span>
                <button type="button" onClick={() => runGate(gate.id)} disabled={busy || !controlsEnabled} aria-label={`Run ${gate.name}`}><Play size={13} fill="currentColor" /></button>
              </div>
            ))}
          </div>
        </section>
        <section className="console-panel">
          <header>
            <div className="console-dots"><i /><i /><i /></div>
            <span><TerminalSquare size={14} /> CONTROL OUTPUT</span>
            {active && <RunBadge status={active.status} />}
          </header>
          {active ? (
            <>
              <div className="console-meta"><strong>{active.gateName}</strong><span>{active.mode.toUpperCase()} / {active.id.slice(0, 8)}</span></div>
              <pre>{active.output || (active.status === 'running' ? 'Gate process is running…\nLive result will be sealed when the process exits.' : 'Run accepted. Waiting for process output…')}</pre>
              <footer><span>RETURN {active.returnCode ?? '—'}</span><span>ELAPSED {elapsed(active.elapsedSeconds)}</span><span>{shortTime(active.finishedAt ?? active.startedAt)}</span></footer>
            </>
          ) : (
            <div className="console-empty"><TerminalSquare size={26} /><strong>No run selected</strong><span>Execute a gate to capture bounded output.</span></div>
          )}
          {snapshot.runs.length > 1 && (
            <div className="run-tabs">
              {snapshot.runs.slice(0, 4).map((run) => <button className={run.id === active?.id ? 'is-active' : ''} type="button" key={run.id} onClick={() => setSelected(run.id)}>{run.gateId}</button>)}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function AgentsView({ snapshot }: { snapshot: Snapshot }) {
  const demo = snapshot.deployment.mode === 'demo'
  return (
    <div className="view">
      <SectionHeading overline={demo ? 'PUBLIC SAMPLE FEED' : 'LOCAL JOURNAL OBSERVER'} title="Human + agent watchfloor" detail={demo ? 'Synthetic records demonstrate the operating model without exposing local tasks, paths, or transcripts.' : 'Bounded operational metadata from the existing append-only Mission Control observer. No transcript content is copied.'} />
      <div className="agent-stats">
        <Stat label="OBSERVER" value={demo ? 'DEMO' : (snapshot.agents.online ? 'ONLINE' : 'OFFLINE')} hint={demo ? 'Synthetic + redacted' : '127.0.0.1:8091'} icon={<Radio size={19} />} />
        <Stat label="ACTIVE / GLOBAL" value={snapshot.agents.activeCount} hint={`${snapshot.agents.blockedCount} blocked`} icon={<Activity size={19} />} />
        <Stat label="THIS PROGRAM" value={snapshot.agents.securityTeamCount ?? 0} hint="Matched by workspace" icon={<Users size={19} />} />
        <Stat label="SOURCE LEDGER" value={snapshot.agents.ledger.ok ? 'VALID' : 'UNKNOWN'} hint={`${snapshot.agents.ledger.checked ?? 0} records checked`} icon={<Fingerprint size={19} />} />
      </div>
      <div className="agent-layout">
        <section className="panel session-panel">
          <div className="panel-heading"><div><span>ATTACHED SESSIONS</span><h2>Security-team activity</h2></div><Bot size={17} /></div>
          <div className="session-list">
            {snapshot.agents.sessions.map((session) => (
              <article className="session" key={`${session.agent}-${session.sessionId}`}>
                <div className="session__avatar">{session.agent.slice(0, 1)}</div>
                <div className="session__body">
                  <header><strong>{session.agent}</strong><RunBadge status={session.status} /><small>{shortTime(session.eventTime)}</small></header>
                  <p>{session.task}</p>
                  {session.nextAction && <div><ChevronRight size={13} /><span>{session.nextAction}</span></div>}
                </div>
              </article>
            ))}
            {snapshot.agents.sessions.length === 0 && <div className="empty-row"><Bot size={20} /><span>No matching active session<br /><small>The observer remains connected.</small></span></div>}
          </div>
        </section>
        <section className="panel collision-panel">
          <div className="panel-heading"><div><span>CONCURRENCY SAFETY</span><h2>Workspace collisions</h2></div><AlertTriangle size={17} /></div>
          {(snapshot.agents.collisions ?? []).map((collision) => (
            <article className="collision" key={`${collision.workspace}-${collision.branch}`}>
              <span>{collision.sessions.length} SESSIONS</span><strong>{collision.workspace}</strong><p>{collision.reason}</p>
            </article>
          ))}
          {(snapshot.agents.collisions ?? []).length === 0 && <div className="safe-state"><Check size={18} /><span>No shared-workspace collision detected</span></div>}
        </section>
      </div>
    </div>
  )
}

function EvidenceView({ snapshot }: { snapshot: Snapshot }) {
  return (
    <div className="view">
      <SectionHeading overline="CHAINED PROVENANCE" title="Evidence, not theater." detail="Readiness remains distinct from engineering health. Every operator action is appended to a local hash chain." />
      <div className="evidence-hero">
        <div className={`ledger-seal ${snapshot.controlLedger.ok ? 'is-valid' : 'is-invalid'}`}>
          <Fingerprint size={34} />
          <span>CONTROL LEDGER</span>
          <strong>{snapshot.controlLedger.ok ? 'CHAIN VALID' : 'CHAIN BROKEN'}</strong>
          <small>{snapshot.controlLedger.entries} entries · {snapshot.controlLedger.head.slice(0, 16)}</small>
        </div>
        <div className="repo-card">
          <GitBranch size={20} />
          <div><span>AUTHORITATIVE WORKTREE</span><strong>{snapshot.repo.branch}</strong><small>{snapshot.repo.commit} · {snapshot.repo.subject}</small></div>
          <em className={snapshot.repo.dirty ? 'is-dirty' : ''}>{snapshot.repo.dirty ? `${snapshot.repo.changedCount} CHANGES` : 'CLEAN'}</em>
        </div>
      </div>
      <div className="evidence-grid">
        <section className="panel">
          <div className="panel-heading"><div><span>READINESS EVIDENCE</span><h2>Hard-gate registry</h2></div><span className="counter">{snapshot.program.verified}/{snapshot.program.total}</span></div>
          <div className="evidence-gates">{snapshot.program.gates.map((gate) => <ReadinessItem gate={gate} key={gate.id} />)}</div>
        </section>
        <section className="panel">
          <div className="panel-heading"><div><span>OPERATOR PROVENANCE</span><h2>Audit chain</h2></div><Fingerprint size={17} /></div>
          <div className="audit-chain">
            {snapshot.activity.map((item) => (
              <div className="audit-item" key={item.id}><i /><div><strong>{item.summary}</strong><span>{shortTime(item.at)} · {item.hash.slice(0, 12)}</span></div></div>
            ))}
            {snapshot.activity.length === 0 && <div className="empty-row"><Fingerprint size={19} /><span>Genesis state<br /><small>The first operator action starts the chain.</small></span></div>}
          </div>
        </section>
        <section className="panel worktree-panel">
          <div className="panel-heading"><div><span>WORKTREE SIGNAL</span><h2>Current changes</h2></div><GitBranch size={17} /></div>
          <div className="change-list">{snapshot.repo.changes.map((change) => <code key={change}>{change}</code>)}</div>
        </section>
      </div>
    </div>
  )
}

const engagementTemplates = [
  { type: 'own-site', label: 'My live site', detail: 'Authorized external posture, application, API, identity and recovery validation.', icon: Globe2 },
  { type: 'pre-launch', label: 'Pre-launch review', detail: 'All seven teams challenge a build before customers or production data arrive.', icon: ClipboardCheck },
  { type: 'client-assessment', label: 'Client engagement', detail: 'Keep client scope, evidence, findings, remediation and reporting separated.', icon: Users },
  { type: 'continuous', label: 'Continuous assurance', detail: 'Repeat the same contract and compare drift, new findings and verified fixes.', icon: GitCompareArrows },
] as const

const securityTeams: SecurityTeam[] = ['purple', 'white', 'yellow', 'green', 'orange', 'blue', 'red']

function EngagementEditor({ onClose, onCreate }: { onClose: () => void; onCreate: (input: EngagementCreateInput) => Promise<void> }) {
  const [values, setValues] = useState({
    name: '',
    clientName: '',
    engagementType: 'pre-launch' as EngagementCreateInput['engagementType'],
    objective: 'Prove this system is safe and ready for launch, identify exploitable gaps, and produce prioritized remediation with reproducible evidence.',
    scopeRules: 'Test only the targets listed here. Avoid destructive actions, denial of service, social engineering, and access to real customer data unless separately approved in writing.',
    authorizationBasis: 'asset-owner' as EngagementCreateInput['authorizationBasis'],
    authorizationAttestation: '',
    authorizationExpiresAt: '',
  })
  const [targets, setTargets] = useState<EngagementCreateInput['targets']>([
    { kind: 'website', displayName: 'Primary application', locator: '', environment: 'staging', notes: '' },
  ])
  const [teams, setTeams] = useState<SecurityTeam[]>(securityTeams)
  const [authorized, setAuthorized] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!authorized) {
      setError('You must record explicit authority before this engagement can be created.')
      return
    }
    setBusy(true)
    setError(null)
    void onCreate({
      ...values,
      clientName: values.clientName || undefined,
      authorizationExpiresAt: values.authorizationExpiresAt ? new Date(values.authorizationExpiresAt).toISOString() : undefined,
      authorizationConfirmed: true,
      selectedTeams: teams,
      targets,
    }).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Unable to create engagement')
      setBusy(false)
    })
  }

  const updateTarget = (index: number, patch: Partial<EngagementCreateInput['targets'][number]>) => {
    setTargets((current) => current.map((target, targetIndex) => targetIndex === index ? { ...target, ...patch } : target))
  }

  return (
    <Modal onClose={onClose} label="Create an authorized security engagement" className="engagement-editor-modal">
      <form className="engagement-editor" onSubmit={submit}>
        <header>
          <span className="eyebrow">AUTHORIZED WORK ORDER</span>
          <h2>Create a security engagement</h2>
          <p>Scope the work once, attach every asset and result to it, then compare each later assessment against the same contract.</p>
        </header>
        <div className="engagement-template-picker" role="group" aria-label="Engagement type">
          {engagementTemplates.map((template) => {
            const Icon = template.icon
            return <button type="button" className={values.engagementType === template.type ? 'is-active' : ''} key={template.type} onClick={() => setValues((current) => ({ ...current, engagementType: template.type }))}><Icon size={16} /><span><strong>{template.label}</strong><small>{template.detail}</small></span></button>
          })}
        </div>
        <div className="editor-grid">
          <label><span>Engagement name</span><input required minLength={3} maxLength={160} value={values.name} onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} placeholder="August launch readiness" /></label>
          <label><span>Client / business</span><input maxLength={160} value={values.clientName} onChange={(event) => setValues((current) => ({ ...current, clientName: event.target.value }))} placeholder="Internal or client name" /></label>
        </div>
        <label><span>What must the teams prove?</span><textarea required minLength={10} maxLength={4000} rows={3} value={values.objective} onChange={(event) => setValues((current) => ({ ...current, objective: event.target.value }))} /></label>
        <section className="target-builder">
          <div className="target-builder__heading"><div><span>TARGETS</span><strong>Explicitly in scope</strong></div><button type="button" onClick={() => setTargets((current) => [...current, { kind: 'website', displayName: '', locator: '', environment: 'unknown', notes: '' }])}><Plus size={14} /> Add target</button></div>
          {targets.map((target, index) => (
            <div className="target-row" key={index}>
              <select aria-label={`Target ${index + 1} type`} value={target.kind} onChange={(event) => updateTarget(index, { kind: event.target.value as EngagementCreateInput['targets'][number]['kind'] })}>
                <option value="website">Website</option><option value="api">API</option><option value="repository">Repository</option><option value="cloud">Cloud</option><option value="mobile">Mobile</option><option value="network">Network</option><option value="artifact">Build artifact</option><option value="media">Media</option><option value="other">Other</option>
              </select>
              <input aria-label={`Target ${index + 1} name`} required minLength={2} maxLength={180} value={target.displayName} onChange={(event) => updateTarget(index, { displayName: event.target.value })} placeholder="Target name" />
              <input aria-label={`Target ${index + 1} locator`} required minLength={2} maxLength={2000} value={target.locator} onChange={(event) => updateTarget(index, { locator: event.target.value })} placeholder="https://staging.example.com" />
              <select aria-label={`Target ${index + 1} environment`} value={target.environment} onChange={(event) => updateTarget(index, { environment: event.target.value as EngagementCreateInput['targets'][number]['environment'] })}><option value="development">Development</option><option value="staging">Staging</option><option value="production">Production</option><option value="client">Client</option><option value="unknown">Unknown</option></select>
              {targets.length > 1 && <button type="button" aria-label={`Remove target ${index + 1}`} onClick={() => setTargets((current) => current.filter((_, targetIndex) => targetIndex !== index))}><X size={14} /></button>}
            </div>
          ))}
        </section>
        <label><span>Rules, exclusions and stop conditions</span><textarea required minLength={10} maxLength={10000} rows={3} value={values.scopeRules} onChange={(event) => setValues((current) => ({ ...current, scopeRules: event.target.value }))} /></label>
        <section className="team-selector">
          <span>TEAMS ASSIGNED</span>
          <div>{securityTeams.map((team) => <button type="button" key={team} className={teams.includes(team) ? `is-active team-${team}` : ''} onClick={() => setTeams((current) => current.includes(team) ? current.filter((item) => item !== team) : [...current, team])}><i />{words(team)}</button>)}</div>
        </section>
        <section className="authorization-box">
          <div className="editor-grid">
            <label><span>Authority basis</span><select value={values.authorizationBasis} onChange={(event) => setValues((current) => ({ ...current, authorizationBasis: event.target.value as EngagementCreateInput['authorizationBasis'] }))}><option value="asset-owner">I own/control these assets</option><option value="internal-approval">Internal written approval</option><option value="written-client-authorization">Written client authorization</option><option value="bug-bounty-scope">Published bug-bounty scope</option></select></label>
            <label><span>Authorization expires (optional)</span><input type="datetime-local" value={values.authorizationExpiresAt} onChange={(event) => setValues((current) => ({ ...current, authorizationExpiresAt: event.target.value }))} /></label>
          </div>
          <label><span>Authority reference / attestation</span><textarea required minLength={12} maxLength={600} rows={2} value={values.authorizationAttestation} onChange={(event) => setValues((current) => ({ ...current, authorizationAttestation: event.target.value }))} placeholder="I own this staging system and authorize the listed non-destructive testing through launch." /></label>
          <label className="authorization-check"><input type="checkbox" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} /><span><strong>I confirm I am authorized to test every listed target.</strong><small>AEGIS will preserve this decision in the tenant audit chain and stop when authority expires.</small></span></label>
        </section>
        {error && <div className="form-error"><AlertTriangle size={15} />{error}</div>}
        <footer><button type="button" className="button button--quiet" onClick={onClose}>Cancel</button><button className="button button--primary" disabled={busy || !authorized || teams.length === 0}><Target size={15} />{busy ? 'Creating…' : 'Create engagement'}</button></footer>
      </form>
    </Modal>
  )
}

function EngagementsView({ snapshot, engagements, controlsEnabled, onNew, onUpload, onLaunch, onAnalyze, onCompare, onOpenWorkspace, engagementExportUrl, evidenceDownloadUrl }: {
  snapshot: Snapshot
  engagements: Engagement[]
  controlsEnabled: boolean
  onNew: () => void
  onUpload: (engagementId: string, files: File[]) => Promise<void>
  onLaunch: (engagementId: string, mode: 'safe' | 'standard' | 'deep', connectorId?: string, baselineRunId?: string) => Promise<void>
  onAnalyze: (engagementId: string, assetId: string, connectorId?: string) => Promise<void>
  onCompare: (engagementId: string, baselineRunId: string, currentRunId: string) => Promise<RunComparison>
  onOpenWorkspace?: () => void
  engagementExportUrl: (engagementId: string) => string | null
  evidenceDownloadUrl: (evidenceId: string) => string | null
}) {
  const [selectedId, setSelectedId] = useState<string | null>(engagements[0]?.id ?? null)
  const [mode, setMode] = useState<'safe' | 'standard' | 'deep'>('safe')
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; message: string } | null>(null)
  const [comparison, setComparison] = useState<RunComparison | null>(null)
  const active = engagements.find((engagement) => engagement.id === selectedId) ?? engagements[0]
  const executor = snapshot.platform?.connectors.find((connector) => connector.capabilities.includes('assessment.execute'))
  const analyzer = snapshot.platform?.connectors.find((connector) => connector.capabilities.includes('evidence.analyze'))

  useEffect(() => {
    if (!active && engagements[0]) setSelectedId(engagements[0].id)
  }, [active, engagements])

  const upload = (files: File[]) => {
    if (!active || files.length === 0) return
    setBusy('upload')
    setNotice(null)
    void onUpload(active.id, files)
      .then(() => setNotice({ tone: 'ok', message: `${files.length} encrypted asset${files.length === 1 ? '' : 's'} attached and quarantined for scanning.` }))
      .catch((reason: unknown) => setNotice({ tone: 'error', message: reason instanceof Error ? reason.message : 'Upload failed' }))
      .finally(() => setBusy(null))
  }

  const launch = () => {
    if (!active || !executor) return
    setBusy('launch')
    setNotice(null)
    const baseline = active.runs.find((run) => run.status === 'completed')?.id
    void onLaunch(active.id, mode, executor.id, baseline)
      .then(() => setNotice({ tone: 'ok', message: 'Assessment work order created. Human approval is required before the connector can execute it.' }))
      .catch((reason: unknown) => setNotice({ tone: 'error', message: reason instanceof Error ? reason.message : 'Launch failed' }))
      .finally(() => setBusy(null))
  }

  const compare = () => {
    if (!active || active.runs.length < 2) return
    setBusy('compare')
    void onCompare(active.id, active.runs[1].id, active.runs[0].id)
      .then(setComparison)
      .catch((reason: unknown) => setNotice({ tone: 'error', message: reason instanceof Error ? reason.message : 'Comparison failed' }))
      .finally(() => setBusy(null))
  }

  const analyze = (assetId: string) => {
    if (!active || !analyzer) return
    setBusy(`analysis-${assetId}`)
    setNotice(null)
    void onAnalyze(active.id, assetId, analyzer.id)
      .then(() => setNotice({ tone: 'ok', message: 'The clean asset was queued for connector analysis. Results and suggestions will return to this engagement.' }))
      .catch((reason: unknown) => setNotice({ tone: 'error', message: reason instanceof Error ? reason.message : 'Analysis failed' }))
      .finally(() => setBusy(null))
  }

  if (!snapshot.platform) {
    return (
      <div className="view engagements-view">
        <SectionHeading overline="AUTHORIZED SECURITY WORK" title="Bring the target. Keep the proof." detail="AEGIS turns an owned site, pre-launch build, or client assessment into a scoped seven-team engagement with durable evidence, repeatable runs, comparison, and export." />
        <div className="engagement-template-grid">{engagementTemplates.map((template) => { const Icon = template.icon; return <article key={template.type}><Icon size={20} /><strong>{template.label}</strong><p>{template.detail}</p><span>WORKSPACE-ISOLATED</span></article> })}</div>
        <TenantOnly nested title="Public mode demonstrates the workflow without accepting targets." detail="Customer workspaces receive drag-and-drop intake, authorization records, encrypted assets, governed team execution, comparisons, and export. The public showcase cannot collect data or launch tests." />
      </div>
    )
  }

  return (
    <div className="view engagements-view">
      <SectionHeading overline="ENGAGEMENT OPERATIONS" title="Scope once. Test safely. Prove the change." detail="Every target, file, team action, finding, decision and later comparison stays inside this tenant and its audit chain." action={controlsEnabled ? <button type="button" className="button button--primary" onClick={onNew}><Plus size={15} /> New engagement</button> : undefined} />
      {engagements.length === 0 ? (
        <div className="engagement-empty">
          <div className="engagement-template-grid">{engagementTemplates.map((template) => { const Icon = template.icon; return <article key={template.type}><Icon size={20} /><strong>{template.label}</strong><p>{template.detail}</p></article> })}</div>
          <div><Target size={28} /><h2>Your first work order starts here.</h2><p>Record authority, define the exact target and stop conditions, then attach the site, repository, documents, screenshots, audio, video or other evidence.</p>{controlsEnabled && <button type="button" className="button button--primary" onClick={onNew}><Plus size={15} /> Create engagement</button>}</div>
        </div>
      ) : (
        <div className="engagement-console">
          <aside className="engagement-register panel">
            <div className="panel-heading"><div><span>WORK REGISTER</span><h2>{engagements.length} engagement{engagements.length === 1 ? '' : 's'}</h2></div><FolderOpen size={17} /></div>
            <div>{engagements.map((engagement) => <button type="button" key={engagement.id} className={active?.id === engagement.id ? 'is-active' : ''} onClick={() => { setSelectedId(engagement.id); setComparison(null) }}><span className={`engagement-status is-${engagement.status}`}><i />{words(engagement.status)}</span><strong>{engagement.name}</strong><small>{engagement.clientName || words(engagement.engagementType)} · {engagement.targets.length} target{engagement.targets.length === 1 ? '' : 's'}</small><em>{engagement.findings.length} findings</em></button>)}</div>
          </aside>
          {active && <div className="engagement-detail">
            <section className="engagement-hero panel">
              <div><span className="eyebrow">{words(active.engagementType)} / {active.clientName || snapshot.platform.workspace.name}</span><h2>{active.name}</h2><p>{active.objective}</p></div>
              <div className="engagement-hero__actions">{engagementExportUrl(active.id) && <a className="button button--quiet" href={engagementExportUrl(active.id) ?? undefined} download><Download size={15} /> Export package</a>}{controlsEnabled && <button type="button" className="button button--primary" disabled={!executor || busy === 'launch'} onClick={launch}><Play size={15} />{busy === 'launch' ? 'Queuing…' : 'Queue assessment'}</button>}</div>
              <div className="engagement-metrics"><span><strong>{active.targets.length}</strong><small>Targets</small></span><span><strong>{active.assets.length}</strong><small>Assets</small></span><span><strong>{active.runs.length}</strong><small>Runs</small></span><span><strong>{active.findings.length}</strong><small>Findings</small></span></div>
            </section>
            {notice && <div className={`engagement-notice is-${notice.tone}`}>{notice.tone === 'ok' ? <Check size={15} /> : <AlertTriangle size={15} />}{notice.message}</div>}
            <div className="engagement-detail-grid">
              <section className="panel scope-card">
                <div className="panel-heading"><div><span>AUTHORITY + SCOPE</span><h2>Fail-closed work boundary</h2></div><LockKeyhole size={17} /></div>
                <div className="authorization-seal"><ShieldCheck size={22} /><div><strong>AUTHORITY RECORDED</strong><span>{words(active.authorization.basis)} · {active.authorization.expiresAt ? `expires ${new Date(active.authorization.expiresAt).toLocaleDateString()}` : 'no recorded expiry'}</span></div></div>
                <p>{active.scopeRules}</p>
                <div className="target-list">{active.targets.map((target) => <article key={target.id}><Globe2 size={15} /><div><strong>{target.displayName}</strong><code>{target.locator}</code></div><span>{words(target.environment)}</span></article>)}</div>
              </section>
              <section className="panel launch-card">
                <div className="panel-heading"><div><span>EXECUTION CONTRACT</span><h2>Seven-team work order</h2></div><Users size={17} /></div>
                <div className="team-run-strip">{active.selectedTeams.map((team) => <span key={team} className={`team-${team}`}><i />{team.slice(0, 2).toUpperCase()}</span>)}</div>
                <label><span>Assessment depth</span><select value={mode} onChange={(event) => setMode(event.target.value as 'safe' | 'standard' | 'deep')}><option value="safe">Safe — passive + non-destructive</option><option value="standard">Standard — authorized active validation</option><option value="deep">Deep — expanded tests, still within scope</option></select></label>
                {executor ? <div className="executor-state is-ready"><Radio size={14} /><span><strong>{executor.name}</strong> allowlisted for assessment.execute</span></div> : <div className="executor-state is-blocked"><AlertTriangle size={14} /><span><strong>Executor required.</strong> Provision a tenant connector with assessment.execute; AEGIS will not pretend work ran without one.</span>{controlsEnabled && <button type="button" onClick={onOpenWorkspace}>Open workspace controls</button>}</div>}
                <small>Every launch creates one high-risk work order and human approval. Destructive actions remain separately gated.</small>
              </section>
              <section className="panel asset-card">
                <div className="panel-heading"><div><span>SECURE INTAKE</span><h2>Files, media and evidence</h2></div><Upload size={17} /></div>
                {controlsEnabled && <label className={`engagement-dropzone ${busy === 'upload' ? 'is-busy' : ''}`} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); upload(Array.from(event.dataTransfer.files)) }}><input type="file" multiple onChange={(event) => { upload(Array.from(event.target.files ?? [])); event.target.value = '' }} /><Upload size={22} /><strong>{busy === 'upload' ? 'Encrypting and attaching…' : 'Drop anything relevant here'}</strong><span>Documents · repositories as archives · screenshots · audio · video · logs · JSON/CSV · build artifacts</span><small>Files are encrypted per tenant and quarantined before analysis or download.</small></label>}
                <div className="asset-list">{active.assets.slice(0, 8).map((asset) => <article key={asset.id}><FileCheck2 size={15} /><div><strong>{asset.filename}</strong><span>{words(asset.mediaKind)} · {bytes(asset.sizeBytes)} · SHA {asset.sha256.slice(0, 10)} · {words(asset.analysisStatus)}</span></div><em className={`is-${asset.scanStatus}`}>{words(asset.scanStatus)}</em><div className="asset-file-actions">{asset.scanStatus === 'clean' && evidenceDownloadUrl(asset.evidenceId) && <a href={evidenceDownloadUrl(asset.evidenceId) ?? undefined} download aria-label={`Download ${asset.filename}`}><Download size={14} /></a>}{asset.scanStatus === 'clean' && analyzer && controlsEnabled && <button type="button" disabled={busy === `analysis-${asset.id}` || asset.analysisStatus === 'queued'} onClick={() => analyze(asset.id)} aria-label={`Analyze ${asset.filename}`}><Sparkles size={14} /></button>}</div></article>)}</div>
                {active.assets[0]?.suggestions?.length > 0 && <div className="suggestion-box"><Sparkles size={16} /><div><strong>Suggested next reviews</strong>{active.assets[0].suggestions.map((suggestion) => <p key={`${suggestion.team}-${suggestion.title}`}><b>{words(suggestion.team)}</b> · {suggestion.title} — {suggestion.detail}</p>)}</div></div>}
              </section>
              <section className="panel history-card">
                <div className="panel-heading"><div><span>DURABLE HISTORY</span><h2>Runs and comparison</h2></div>{active.runs.length >= 2 && <button type="button" onClick={compare} disabled={busy === 'compare'}><GitCompareArrows size={14} /> Compare latest</button>}</div>
                <div className="run-history">{active.runs.map((run) => <article key={run.id}><span>#{String(run.sequence).padStart(2, '0')}</span><div><strong>{words(run.mode)} assessment</strong><small>{shortTime(run.createdAt)} · {run.taskId ? `task ${run.taskId.slice(0, 8)}` : 'plan only'}</small></div><RunBadge status={run.status} />{run.score != null && <em>{run.score}/100</em>}</article>)}{active.runs.length === 0 && <div className="empty-row"><Clock3 size={18} /><span>No assessment runs yet<br /><small>The first approved work order becomes the baseline.</small></span></div>}</div>
                {comparison && <div className="comparison-strip"><span className="is-new"><strong>{comparison.counts.introduced}</strong><small>Introduced</small></span><span><strong>{comparison.counts.persistent}</strong><small>Persistent</small></span><span className="is-resolved"><strong>{comparison.counts.resolved}</strong><small>Resolved</small></span></div>}
                <div className="finding-list">{active.findings.slice(0, 8).map((finding) => <article key={finding.id}><i className={`severity-${finding.severity}`} /><div><strong>{finding.title}</strong><span>{finding.ownerTeam ? words(finding.ownerTeam) : 'Unassigned'} · {words(finding.status)}</span></div><em>{finding.severity.toUpperCase()}</em></article>)}</div>
              </section>
            </div>
          </div>}
        </div>
      )}
    </div>
  )
}

function TenantOnly({ title, detail, nested = false }: { title: string; detail: string; nested?: boolean }) {
  return (
    <div className="tenant-only">
      <LockKeyhole size={28} />
      {nested ? <h2>{title}</h2> : <h1 data-view-heading tabIndex={-1}>{title}</h1>}
      <p>{detail}</p>
      <span>AVAILABLE IN AN ISOLATED CUSTOMER WORKSPACE</span>
    </div>
  )
}

function CoverageStatus({ status }: { status: SecurityControl['status'] }) {
  return <span className={`coverage-status is-${status}`}><i />{status === 'telemetry-gap' ? 'Telemetry gap' : words(status)}</span>
}

function CoverageView({ snapshot }: { snapshot: Snapshot }) {
  const platform = snapshot.platform
  if (!platform) {
    return <TenantOnly title="Coverage controls stay with the customer." detail="The private operator console does not expose hosted customer policy. A customer workspace receives its own control baseline, telemetry map, and evidence state." />
  }
  const coverage = platform.securityCoverage
  const teamOrder = ['purple', 'white', 'yellow', 'green', 'orange', 'blue', 'red']
  const teamById = new Map(snapshot.teams.map((team) => [team.id, team]))
  return (
    <div className="view coverage-view">
      <SectionHeading
        overline="PROVEN / CONFIGURED / UNKNOWN"
        title="Every defense has an owner. Every gap stays visible."
        detail="AEGIS maps prevention, discovery, detection, response, recovery, governance, and validation across the seven-team operating model. Configured controls are never promoted to verified without their required telemetry."
      />
      <section className="coverage-command" aria-label="Security coverage summary">
        <div className="coverage-command__score">
          <span>OBSERVABLE COVERAGE</span>
          <strong>{coverage.summary.coveragePercent.toFixed(1)}<small>%</small></strong>
          <p>{coverage.summary.observable} of {coverage.summary.enabled} enabled controls have a live or internal evidence source.</p>
        </div>
        <div className="coverage-command__bands">
          <div><span>Verified</span><strong>{coverage.summary.verified}</strong></div>
          <div><span>Configured</span><strong>{coverage.summary.observable - coverage.summary.verified}</strong></div>
          <div className={coverage.summary.telemetryGaps ? 'is-alert' : ''}><span>Telemetry gaps</span><strong>{coverage.summary.telemetryGaps}</strong></div>
          <div><span>Exceptions</span><strong>{coverage.summary.exceptions}</strong></div>
        </div>
        <div className="coverage-command__sources">
          <span>CONNECTED SIGNALS</span>
          <div>{coverage.sources.length ? coverage.sources.map((source) => <code key={source}>{source}</code>) : <em>No customer telemetry connected</em>}</div>
        </div>
      </section>
      <section className="coverage-matrix" aria-label="Seven-team security control matrix">
        {teamOrder.map((teamId) => {
          const team = teamById.get(teamId)
          const controls = coverage.controls.filter((control) => control.ownerTeam === teamId)
          const gaps = controls.filter((control) => control.status === 'telemetry-gap').length
          return (
            <article className={`coverage-lane team-${teamId}`} key={teamId} style={{ '--team': team?.color } as CSSProperties}>
              <header>
                <div className="coverage-lane__team"><b>{teamId.slice(0, 2).toUpperCase()}</b><span><strong>{team?.name ?? words(teamId)}</strong><small>{team?.verb ?? 'Protect'}</small></span></div>
                <div className={gaps ? 'coverage-lane__gap is-alert' : 'coverage-lane__gap'}><strong>{gaps}</strong><span>{gaps === 1 ? 'gap' : 'gaps'}</span></div>
              </header>
              <div className="coverage-lane__controls">
                {controls.map((control) => (
                  <details key={control.id} className="coverage-control">
                    <summary><CoverageStatus status={control.status} /><strong>{control.title}</strong><span>{control.modes.join(' · ')}</span><ChevronRight size={14} /></summary>
                    <div><p>{control.objective}</p><code>source: {control.requiredSource}</code><code>domain: {control.domain}</code></div>
                  </details>
                ))}
              </div>
            </article>
          )
        })}
      </section>
    </div>
  )
}

function ShadowAIView({
  snapshot,
  controlsEnabled,
  onAssetDecision,
  onViolationDecision,
  onEditPolicy,
}: {
  snapshot: Snapshot
  controlsEnabled: boolean
  onAssetDecision: (assetId: string, disposition: 'approved' | 'restricted' | 'blocked') => void
  onViolationDecision: (violationId: string, status: 'acknowledged' | 'resolved' | 'false-positive') => void
  onEditPolicy: () => void
}) {
  const shadow = snapshot.platform?.shadowAI
  if (!shadow) {
    return <TenantOnly title="Shadow AI defense needs customer-owned signals." detail="The public showcase uses synthetic examples only. In a customer workspace, outbound connectors correlate network, endpoint, gateway, cloud, model, tool, and MCP inventory without collecting prompt content." />
  }
  return (
    <div className="view shadow-view">
      <SectionHeading
        overline="DISCOVER / GOVERN / PREVENT / PROVE"
        title="Shadow AI cannot hide between tools."
        detail="See sanctioned and unsanctioned AI use across people, devices, models, agents, extensions, APIs, and MCP resources. Data classification drives policy; raw prompts and responses never enter this system."
      />
      <section className="shadow-signal">
        <div className="shadow-signal__radar" aria-hidden="true"><i /><i /><i /><span><ScanSearch size={25} /></span></div>
        <div><span>DISCOVERED ASSETS</span><strong>{shadow.counts.assets}</strong><small>{shadow.counts.unsanctioned} awaiting a decision</small></div>
        <div className={shadow.counts.openViolations ? 'is-alert' : ''}><span>OPEN VIOLATIONS</span><strong>{shadow.counts.openViolations}</strong><small>{shadow.counts.blocked} assets marked blocked</small></div>
        <div><span>OBSERVED EGRESS</span><strong>{bytes(shadow.counts.bytesSent)}</strong><small>{shadow.counts.usageEvents} metadata-only usage events</small></div>
        <div><span>ESTIMATED SPEND</span><strong>{moneyFromMicrousd(shadow.counts.estimatedCostMicrousd)}</strong><small>Customer workspace estimate</small></div>
      </section>
      <section className="shadow-policy">
        <div><ShieldCheck size={18} /><span><strong>Sensitive data</strong><small>{words(shadow.policy.sensitiveDataDisposition)}</small></span></div>
        <div><Network size={18} /><span><strong>Unknown AI</strong><small>{words(shadow.policy.defaultDisposition)}</small></span></div>
        <div><Ban size={18} /><span><strong>Blocked domains</strong><small>{shadow.policy.blockedDomains.length}</small></span></div>
        <div><LockKeyhole size={18} /><span><strong>Prompt retention</strong><small>{shadow.policy.retainPromptContent ? 'On' : 'Always off'}</small></span><button type="button" disabled={!controlsEnabled} onClick={onEditPolicy}>Edit policy</button></div>
      </section>
      <div className="shadow-layout">
        <section className="panel shadow-inventory">
          <div className="panel-heading"><div><span>AI ASSET INVENTORY</span><h2>Known, unknown, and governed</h2></div><span className="counter">{shadow.assets.length}</span></div>
          <div className="shadow-table">
            {shadow.assets.map((asset) => (
              <article className="shadow-asset" key={asset.id}>
                <div className={`risk-index is-${asset.disposition}`}><strong>{asset.riskScore}</strong><span>RISK</span></div>
                <div className="shadow-asset__identity"><strong>{asset.name}</strong><span>{asset.vendor} · {words(asset.category)} · {asset.source}</span><small>{[...asset.models, ...asset.tools, ...asset.mcpServers].slice(0, 4).join(' · ') || 'Metadata discovery pending'}</small></div>
                <CoverageStatus status={asset.disposition === 'unknown' ? 'telemetry-gap' : asset.disposition === 'approved' ? 'verified' : asset.disposition === 'restricted' ? 'configured' : 'exception'} />
                <div className="asset-actions">
                  <button type="button" disabled={!controlsEnabled} onClick={() => onAssetDecision(asset.id, 'approved')}>Approve</button>
                  <button type="button" disabled={!controlsEnabled} onClick={() => onAssetDecision(asset.id, 'restricted')}>Restrict</button>
                  <button type="button" className="is-danger" disabled={!controlsEnabled} onClick={() => onAssetDecision(asset.id, 'blocked')}>Mark blocked</button>
                </div>
              </article>
            ))}
            {shadow.assets.length === 0 && <div className="empty-row"><ScanSearch size={19} /><span>No AI assets received<br /><small>Connect endpoint or network discovery to establish coverage.</small></span></div>}
          </div>
        </section>
        <section className="panel violation-queue">
          <div className="panel-heading"><div><span>POLICY VIOLATIONS</span><h2>Decisions required</h2></div><ShieldAlert size={17} /></div>
          <div>
            {shadow.violations.filter((item) => item.status === 'open').map((violation) => (
              <article className={`violation is-${violation.severity}`} key={violation.id}>
                <header><span>{violation.severity}</span><small>{shortTime(violation.createdAt)}</small></header>
                <strong>{violation.summary}</strong><p>{words(violation.ruleId)}</p>
                <footer><button type="button" disabled={!controlsEnabled} onClick={() => onViolationDecision(violation.id, 'acknowledged')}>Acknowledge</button><button type="button" disabled={!controlsEnabled} onClick={() => onViolationDecision(violation.id, 'resolved')}>Resolve</button></footer>
              </article>
            ))}
            {shadow.violations.filter((item) => item.status === 'open').length === 0 && <div className="safe-state"><Check size={18} /><span>No unresolved AI policy violations</span></div>}
          </div>
        </section>
      </div>
    </div>
  )
}

function WorkspaceView({ snapshot, controlsEnabled, onTaskDecision, onEditRetention, onEditSafety, onProvisionConnector }: { snapshot: Snapshot; controlsEnabled: boolean; onTaskDecision: (taskId: string, decision: 'approved' | 'rejected') => void; onEditRetention: () => void; onEditSafety: () => void; onProvisionConnector: () => void }) {
  const platform = snapshot.platform
  if (!platform) {
    return <TenantOnly title="Customer controls are isolated from the private operator." detail="Hosted workspaces receive independent identities, connector credentials, retention, approvals, evidence, and audit history. They cannot inspect this private machine or another customer." />
  }
  const pending = platform.approvals.filter((approval) => approval.status === 'pending')
  const taskById = new Map(platform.tasks.map((task) => [task.id, task]))
  return (
    <div className="view workspace-view">
      <SectionHeading overline="CUSTOMER-OWNED CONTROL PLANE" title={`${platform.workspace.name} controls its own boundary.`} detail="Workspace identity, connector credentials, telemetry, decisions, evidence, and retention are tenant-scoped. No customer data is used to populate the public showcase." />
      <section className="workspace-identity">
        <div><span>WORKSPACE</span><strong>{platform.workspace.slug}</strong><small>{platform.workspace.plan} plan · {platform.workspace.status}</small></div>
        <div><span>YOUR ROLE</span><strong>{words(platform.user.role)}</strong><small>{platform.user.email}</small></div>
        <div><span>SAFETY STATE</span><strong>{words(platform.workspace.safetyLevel)}</strong><small>{platform.workspace.killSwitchActive ? 'Kill switch engaged' : 'Command queue governed'}</small><button type="button" disabled={!controlsEnabled} onClick={onEditSafety}>Change state</button></div>
        <div><span>AUDIT LEDGER</span><strong>{platform.ledger.ok ? 'Verified' : 'Fault'}</strong><small>{platform.ledger.entries} chained events</small></div>
      </section>
      <div className="workspace-grid">
        <section className="panel connector-board">
          <div className="panel-heading"><div><span>OUTBOUND-ONLY CONNECTORS</span><h2>Customer signal plane</h2></div><button type="button" className="panel-action" disabled={!controlsEnabled} onClick={onProvisionConnector}>Add connector</button></div>
          <div>
            {platform.connectors.map((connector) => <article key={connector.id}><span className={`connector-state is-${connector.status}`}><i />{connector.status}</span><strong>{connector.name}</strong><small>v{connector.version} · {connector.capabilities.length} scoped capabilities</small><code>{connector.capabilities.slice(0, 4).join(' · ')}</code></article>)}
            {platform.connectors.length === 0 && <div className="empty-row"><Network size={19} /><span>No connector provisioned<br /><small>Create a scoped credential to begin onboarding.</small></span></div>}
          </div>
        </section>
        <section className="panel approval-board">
          <div className="panel-heading"><div><span>HUMAN AUTHORIZATION</span><h2>Approval queue</h2></div><span className="counter">{pending.length}</span></div>
          <div>
            {pending.map((approval) => {
              const task = taskById.get(approval.taskId)
              return <article key={approval.id}><div><span>{task?.riskLevel ?? 'high'} risk</span><strong>{task?.title ?? approval.reason}</strong><small>{task?.action ?? approval.reason}</small></div><footer><button type="button" disabled={!controlsEnabled} onClick={() => onTaskDecision(approval.taskId, 'rejected')}>Reject</button><button type="button" className="is-approve" disabled={!controlsEnabled} onClick={() => onTaskDecision(approval.taskId, 'approved')}>Approve</button></footer></article>
            })}
            {pending.length === 0 && <div className="safe-state"><Check size={18} /><span>No actions awaiting approval</span></div>}
          </div>
        </section>
        <section className="panel retention-board">
          <div className="panel-heading"><div><span>DATA LIFECYCLE</span><h2>Retention and legal hold</h2></div><button type="button" className="panel-action" disabled={!controlsEnabled} onClick={onEditRetention}>Edit retention</button></div>
          <div className="retention-track"><span><strong>{platform.retention.telemetryDays}</strong><small>Telemetry days</small></span><i /><span><strong>{platform.retention.taskDays}</strong><small>Task days</small></span><i /><span><strong>{platform.retention.evidenceDays}</strong><small>Evidence days</small></span><i /><span><strong>{platform.retention.auditDays}</strong><small>Audit days</small></span></div>
          <p>{platform.retention.legalHoldDefault ? 'New evidence is placed on legal hold by default.' : 'Legal hold is record-specific. Expired data requires an explicit purge confirmation.'}</p>
        </section>
      </div>
    </div>
  )
}

function listValue(value: string[]): string {
  return value.join('\n')
}

function parseList(value: string): string[] {
  return [...new Set(value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean))]
}

function PolicyEditor({ policy, onClose, onSave }: { policy: ShadowAIData['policy']; onClose: () => void; onSave: (policy: ShadowAIPolicyInput) => void }) {
  const [defaultDisposition, setDefaultDisposition] = useState<ShadowAIPolicyInput['defaultDisposition']>(policy.defaultDisposition as ShadowAIPolicyInput['defaultDisposition'])
  const [sensitiveDataDisposition, setSensitiveDataDisposition] = useState<ShadowAIPolicyInput['sensitiveDataDisposition']>(policy.sensitiveDataDisposition as ShadowAIPolicyInput['sensitiveDataDisposition'])
  const [approvedVendors, setApprovedVendors] = useState(listValue(policy.approvedVendors))
  const [approvedDomains, setApprovedDomains] = useState(listValue(policy.approvedDomains))
  const [blockedDomains, setBlockedDomains] = useState(listValue(policy.blockedDomains))
  const [prohibitedDataLabels, setProhibitedDataLabels] = useState(listValue(policy.prohibitedDataLabels))
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSave({
      defaultDisposition,
      sensitiveDataDisposition,
      approvedVendors: parseList(approvedVendors),
      approvedDomains: parseList(approvedDomains),
      blockedDomains: parseList(blockedDomains),
      prohibitedDataLabels: parseList(prohibitedDataLabels),
      retainPromptContent: false,
    })
  }
  return (
    <Modal onClose={onClose} label="Edit Shadow AI policy">
      <form className="control-form" onSubmit={submit}>
        <span className="eyebrow"><ShieldAlert size={13} /> SHADOW AI POLICY</span>
        <h2>Set the customer’s AI boundary.</h2>
        <p>Discovery records metadata and pseudonymous references. Raw prompts and responses are never retained.</p>
        <div className="form-grid">
          <label><span>Unknown AI</span><select value={defaultDisposition} onChange={(event) => setDefaultDisposition(event.target.value as ShadowAIPolicyInput['defaultDisposition'])}><option value="monitor">Monitor</option><option value="require-approval">Require approval</option><option value="block">Block</option></select></label>
          <label><span>Sensitive data</span><select value={sensitiveDataDisposition} onChange={(event) => setSensitiveDataDisposition(event.target.value as ShadowAIPolicyInput['sensitiveDataDisposition'])}><option value="monitor">Monitor</option><option value="require-approval">Require approval</option><option value="block">Block</option></select></label>
          <label><span>Approved vendors</span><textarea rows={3} value={approvedVendors} onChange={(event) => setApprovedVendors(event.target.value)} placeholder="OpenAI" /></label>
          <label><span>Approved domains</span><textarea rows={3} value={approvedDomains} onChange={(event) => setApprovedDomains(event.target.value)} placeholder="api.openai.com" /></label>
          <label><span>Blocked domains</span><textarea rows={3} value={blockedDomains} onChange={(event) => setBlockedDomains(event.target.value)} placeholder="unapproved.example" /></label>
          <label><span>Prohibited data labels</span><textarea rows={3} value={prohibitedDataLabels} onChange={(event) => setProhibitedDataLabels(event.target.value)} placeholder="credentials&#10;regulated&#10;source-code-secret" /></label>
        </div>
        <div className="control-form__lock"><LockKeyhole size={15} /><span>Prompt-content retention is platform-locked off and cannot be enabled by policy.</span></div>
        <div className="control-form__actions"><button type="button" className="button button--quiet" onClick={onClose}>Cancel</button><button type="submit" className="button button--primary"><ShieldCheck size={15} /> Save policy</button></div>
      </form>
    </Modal>
  )
}

function RetentionEditor({ retention, onClose, onSave }: { retention: RetentionInput; onClose: () => void; onSave: (retention: RetentionInput) => void }) {
  const [values, setValues] = useState(retention)
  const number = (key: keyof Pick<RetentionInput, 'telemetryDays' | 'taskDays' | 'evidenceDays' | 'auditDays'>, value: string) => setValues((current) => ({ ...current, [key]: Number(value) }))
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); onSave(values) }
  return (
    <Modal onClose={onClose} label="Edit retention policy">
      <form className="control-form" onSubmit={submit}>
        <span className="eyebrow"><LockKeyhole size={13} /> DATA LIFECYCLE</span>
        <h2>Own retention by data class.</h2>
        <p>Expiry never bypasses legal hold. A purge remains a separate, explicit confirmed operation.</p>
        <div className="form-grid form-grid--numbers">
          <label><span>Telemetry days</span><input type="number" min={7} max={2555} required value={values.telemetryDays} onChange={(event) => number('telemetryDays', event.target.value)} /></label>
          <label><span>Task days</span><input type="number" min={30} max={3650} required value={values.taskDays} onChange={(event) => number('taskDays', event.target.value)} /></label>
          <label><span>Evidence days</span><input type="number" min={30} max={3650} required value={values.evidenceDays} onChange={(event) => number('evidenceDays', event.target.value)} /></label>
          <label><span>Audit days</span><input type="number" min={365} max={3650} required value={values.auditDays} onChange={(event) => number('auditDays', event.target.value)} /></label>
        </div>
        <label className="check-field"><input type="checkbox" checked={values.legalHoldDefault} onChange={(event) => setValues((current) => ({ ...current, legalHoldDefault: event.target.checked }))} /><span>Place new evidence on legal hold by default</span></label>
        <div className="control-form__actions"><button type="button" className="button button--quiet" onClick={onClose}>Cancel</button><button type="submit" className="button button--primary">Save retention</button></div>
      </form>
    </Modal>
  )
}

function SafetyEditor({ current, onClose, onSave }: { current: string; onClose: () => void; onSave: (level: SafetyLevel, reason: string) => void }) {
  const [level, setLevel] = useState<SafetyLevel>(current as SafetyLevel)
  const [reason, setReason] = useState('Customer-authorized operating state change.')
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); onSave(level, reason) }
  return (
    <Modal onClose={onClose} label="Change workspace safety state">
      <form className="control-form" onSubmit={submit}>
        <span className="eyebrow"><CircleStop size={13} /> EXECUTION SAFETY</span>
        <h2>Control what can run.</h2>
        <p>Restricted limits execution. Halted engages the workspace kill switch and stops task leasing.</p>
        <label><span>Safety state</span><select value={level} onChange={(event) => setLevel(event.target.value as SafetyLevel)}><option value="normal">Normal</option><option value="cautious">Cautious</option><option value="restricted">Restricted</option><option value="halted">Halted — kill switch</option></select></label>
        <label><span>Decision reason</span><textarea rows={3} required minLength={8} maxLength={600} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
        {level === 'halted' && <div className="confirm-dialog__warning"><AlertTriangle size={16} /><span>This stops new connector task leases until the state is changed.</span></div>}
        <div className="control-form__actions"><button type="button" className="button button--quiet" onClick={onClose}>Cancel</button><button type="submit" className={level === 'halted' ? 'button button--danger' : 'button button--primary'}>Apply state</button></div>
      </form>
    </Modal>
  )
}

const observationCapabilities = [
  'observe.status',
  'shadow_ai.assets',
  'shadow_ai.usage',
  'telemetry.network',
  'telemetry.endpoint',
  'telemetry.dlp',
  'telemetry.identity',
  'telemetry.api',
  'telemetry.code',
  'telemetry.cloud',
  'telemetry.asset',
  'telemetry.vulnerability',
  'telemetry.container',
  'telemetry.kubernetes',
  'telemetry.secrets',
  'telemetry.backup',
  'telemetry.email',
  'telemetry.agent',
  'telemetry.ai-gateway',
] as const

function ConnectorEditor({ onClose, onProvision }: { onClose: () => void; onProvision: (name: string, capabilities: string[]) => Promise<{ token: string; warning: string }> }) {
  const [name, setName] = useState('Primary customer edge')
  const [gateExecution, setGateExecution] = useState(false)
  const [assessmentExecution, setAssessmentExecution] = useState(false)
  const [evidenceAnalysis, setEvidenceAnalysis] = useState(false)
  const [shadowEnforcement, setShadowEnforcement] = useState(false)
  const [credential, setCredential] = useState<{ token: string; warning: string } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [working, setWorking] = useState(false)
  const [copied, setCopied] = useState(false)
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setWorking(true)
    setFailure(null)
    const capabilities = [...observationCapabilities, ...(gateExecution ? ['gate.run'] : []), ...(assessmentExecution ? ['assessment.execute'] : []), ...(evidenceAnalysis ? ['evidence.analyze'] : []), ...(shadowEnforcement ? ['shadow_ai.block'] : [])]
    void onProvision(name, capabilities)
      .then(setCredential)
      .catch((reason: unknown) => setFailure(reason instanceof Error ? reason.message : 'Connector provisioning failed'))
      .finally(() => setWorking(false))
  }
  if (credential) {
    return (
      <Modal onClose={onClose} label="Connector credential created">
        <div className="control-form one-time-credential">
          <span className="eyebrow"><Network size={13} /> CONNECTOR CREATED</span>
          <h2>Copy this credential now.</h2>
          <p>{credential.warning} Mission Control stores only a keyed hash and cannot display it again.</p>
          <code>{credential.token}</code>
          <div className="control-form__lock"><LockKeyhole size={15} /><span>Install this only in the customer-owned connector secret store. Never place it in source code or the public showcase.</span></div>
          <div className="control-form__actions"><button type="button" className="button button--quiet" onClick={() => { void navigator.clipboard.writeText(credential.token).then(() => setCopied(true)) }}>{copied ? 'Copied' : 'Copy credential'}</button><button type="button" className="button button--primary" onClick={onClose}>Done</button></div>
        </div>
      </Modal>
    )
  }
  return (
    <Modal onClose={onClose} label="Provision customer connector">
      <form className="control-form" onSubmit={submit}>
        <span className="eyebrow"><Network size={13} /> OUTBOUND CUSTOMER EDGE</span>
        <h2>Provision least-privilege telemetry.</h2>
        <p>The recommended profile observes security and Shadow AI signals. Execution capabilities remain off unless explicitly enabled.</p>
        <label><span>Connector name</span><input type="text" required minLength={2} maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="capability-summary"><strong>{observationCapabilities.length}</strong><span>Read-only observation capabilities<br /><small>Endpoint, network, identity, cloud, application, evidence, and AI metadata</small></span></div>
        <label className="check-field"><input type="checkbox" checked={gateExecution} onChange={(event) => setGateExecution(event.target.checked)} /><span>Allow approved engineering gate execution</span></label>
        <label className="check-field"><input type="checkbox" checked={assessmentExecution} onChange={(event) => setAssessmentExecution(event.target.checked)} /><span>Allow human-approved engagement assessments</span></label>
        <label className="check-field"><input type="checkbox" checked={evidenceAnalysis} onChange={(event) => setEvidenceAnalysis(event.target.checked)} /><span>Allow analysis of clean, tenant-scoped evidence</span></label>
        <label className="check-field"><input type="checkbox" checked={shadowEnforcement} onChange={(event) => setShadowEnforcement(event.target.checked)} /><span>Allow separately approved Shadow AI blocking</span></label>
        {failure && <div className="form-error"><AlertTriangle size={14} />{failure}</div>}
        <div className="control-form__actions"><button type="button" className="button button--quiet" onClick={onClose}>Cancel</button><button type="submit" className="button button--primary" disabled={working}>{working ? 'Provisioning…' : 'Create credential'}</button></div>
      </form>
    </Modal>
  )
}

function Modal({ children, onClose, label, className = '' }: { children: ReactNode; onClose: () => void; label: string; className?: string }) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])
  useLayoutEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const background = Array.from(document.querySelectorAll<HTMLElement>('.app-stage, .nav-rail')).map((element) => ({
      element,
      inert: element.inert,
      ariaHidden: element.getAttribute('aria-hidden'),
    }))
    background.forEach(({ element }) => {
      element.inert = true
      element.setAttribute('aria-hidden', 'true')
    })

    const focusable = () => Array.from(dialog.querySelectorAll<HTMLElement>(
      'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
    )).filter((element) => !element.hasAttribute('hidden') && element.getClientRects().length > 0)
    const initial = dialog.querySelector<HTMLElement>('[data-modal-initial-focus]') ?? focusable()[0] ?? dialog
    let mounted = true
    window.queueMicrotask(() => {
      if (mounted) initial.focus({ preventScroll: true })
    })
    const containFocus = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (items.length === 0) {
        event.preventDefault()
        dialog.focus({ preventScroll: true })
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      const active = document.activeElement
      if (event.shiftKey && (active === first || !dialog.contains(active))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && (active === last || !dialog.contains(active))) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', containFocus, true)
    return () => {
      mounted = false
      document.removeEventListener('keydown', containFocus, true)
      background.forEach(({ element, inert, ariaHidden }) => {
        element.inert = inert
        if (ariaHidden == null) element.removeAttribute('aria-hidden')
        else element.setAttribute('aria-hidden', ariaHidden)
      })
      if (previousFocus && document.contains(previousFocus)) previousFocus.focus({ preventScroll: true })
    }
  }, [])
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={dialogRef} className={`modal ${className}`} role="dialog" aria-modal="true" aria-label={label} tabIndex={-1}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close" data-modal-initial-focus><X size={17} /></button>
        {children}
      </div>
    </div>
  )
}

interface GuideStep {
  title: string
  overline: string
  description: string
  signal: string
  action: string
  view: View
  icon: typeof LayoutDashboard
}

function GuidePanel({ snapshot, setView, onClose }: { snapshot: Snapshot; setView: (view: View) => void; onClose: () => void }) {
  const [step, setStep] = useState(0)
  const demo = snapshot.deployment.mode === 'demo'
  const steps: GuideStep[] = [
    {
      title: 'Read the trust state first.',
      overline: 'START / COMMAND',
      description: 'The readiness ring tells you how much is proven. The assurance interlock tells you whether AEGIS is allowed to make a security claim.',
      signal: 'Pending is not a cosmetic warning. It names work or human authority that is still required.',
      action: 'Open Command and read the readiness contract before touching any control.',
      view: 'overview',
      icon: LayoutDashboard,
    },
    {
      title: 'Turn the request into an authorized work order.',
      overline: 'SCOPE / ENGAGEMENT',
      description: 'Engagements keep the client or product, exact targets, authorization, exclusions, uploaded assets, team plan, findings, reruns and exports in one durable record.',
      signal: demo ? 'Public mode shows this operating model but never accepts targets or files.' : 'A saved engagement is not permission to attack anything outside its recorded scope or authorization window.',
      action: demo ? 'Open Engagements to preview the four supported workflows.' : 'Create the engagement, attest your authority, define stop conditions, then attach the inputs the teams need.',
      view: 'engagements',
      icon: Target,
    },
    {
      title: 'Separate coverage from proof.',
      overline: 'DIAGNOSE / COVERAGE',
      description: 'Security Coverage maps every control to a team and evidence source. Configured means present; observable means signals exist; verified means evidence passed.',
      signal: 'A telemetry gap means AEGIS cannot see enough to verify the control yet.',
      action: 'Start with the red and amber gaps, then identify the missing source or owner.',
      view: 'coverage',
      icon: ScanSearch,
    },
    {
      title: 'Find unsanctioned AI without collecting prompts.',
      overline: 'DISCOVER / SHADOW AI',
      description: 'Shadow AI Defense correlates customer-owned network, endpoint, gateway, cloud, model, tool, extension, local-agent, and MCP inventory signals.',
      signal: demo ? 'Everything here is synthetic. It demonstrates the workflow without exposing owner or customer records.' : 'Asset and usage metadata are retained under policy; raw AI prompt content remains off.',
      action: demo ? 'Inspect the example policy boundary and asset workflow.' : 'Review unknown assets, violations, approved vendors, and prohibited data labels.',
      view: 'shadow',
      icon: ShieldAlert,
    },
    {
      title: demo ? 'Follow the proof trail.' : 'Operate through controlled queues.',
      overline: demo ? 'VERIFY / EVIDENCE' : 'ACT / WORKSPACE',
      description: demo
        ? 'Evidence shows how readiness and activity stay traceable. Public controls are removed, so you can inspect the operating model without changing it.'
        : 'Workspace Controls is where authorized users review approvals, connectors, retention, and safety state. High-risk work stays gated and auditable.',
      signal: demo ? 'Synthetic-only and read-only markings remain visible throughout the tour.' : 'Use the narrowest connector capabilities and require a separate approver for critical actions.',
      action: demo ? 'Finish in Evidence, then use the Guide button anytime you need this orientation again.' : 'Connect observation sources first; only enable execution capabilities when there is a documented need.',
      view: demo ? 'evidence' : 'workspace',
      icon: demo ? FileCheck2 : SlidersHorizontal,
    },
  ]
  const current = steps[step]
  const Icon = current.icon
  const showView = () => {
    setView(current.view)
    onClose()
  }
  return (
    <Modal onClose={onClose} label="Mission Control orientation" className="modal--guide">
      <div className="guide-panel">
        <header className="guide-panel__header">
          <span className="eyebrow"><BookOpen size={13} /> FIELD GUIDE / {demo ? 'PUBLIC SHOWCASE' : 'SECURE WORKSPACE'}</span>
          <h2>Know what you are seeing.<br /><em>Know what to do next.</em></h2>
          <p>{demo ? 'A five-step orientation to the AEGIS proof model. This showcase is safe to explore: its data is synthetic and every control action is removed.' : 'A five-step operating path for a new workspace user. Scope first, act through policy, and verify every outcome.'}</p>
        </header>
        <div className="guide-panel__body">
          <nav className="guide-steps" aria-label="Orientation steps">
            {steps.map((item, index) => (
              <button type="button" key={item.overline} className={step === index ? 'is-active' : ''} onClick={() => setStep(index)} aria-current={step === index ? 'step' : undefined}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <div><small>{item.overline}</small><strong>{item.title}</strong></div>
              </button>
            ))}
          </nav>
          <section className="guide-step" aria-live="polite">
            <div className="guide-step__top"><span>{String(step + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')}</span><Icon size={22} /></div>
            <h3>{current.title}</h3>
            <p>{current.description}</p>
            <div className="guide-callout"><span>WHAT THE SIGNAL MEANS</span><strong>{current.signal}</strong></div>
            <div className="guide-action"><ArrowUpRight size={16} /><div><span>YOUR NEXT MOVE</span><strong>{current.action}</strong></div></div>
            <div className="guide-legend" aria-label="Status legend">
              <span><i className="is-verified" />Verified</span>
              <span><i className="is-waiting" />Waiting</span>
              <span><i className="is-blocked" />Blocked</span>
              <span><i className="is-demo" />Synthetic</span>
            </div>
          </section>
        </div>
        <footer className="guide-panel__footer">
          <button type="button" className="button button--quiet" onClick={() => setStep((value) => Math.max(0, value - 1))} disabled={step === 0}>Back</button>
          <span>Press <kbd>?</kbd> to reopen this guide</span>
          {step < steps.length - 1
            ? <button type="button" className="button button--primary" onClick={() => setStep((value) => Math.min(steps.length - 1, value + 1))}>Next step <ChevronRight size={15} /></button>
            : <button type="button" className="button button--primary" onClick={showView}>Open {demo ? 'evidence' : 'workspace'} <ArrowUpRight size={15} /></button>}
        </footer>
      </div>
    </Modal>
  )
}

function ViewPanel({ scale, density, fullscreen, onScale, onDensity, onFullscreen, onReset, onClose }: { scale: ViewScale; density: ViewDensity; fullscreen: boolean; onScale: (scale: ViewScale) => void; onDensity: (density: ViewDensity) => void; onFullscreen: () => void; onReset: () => void; onClose: () => void }) {
  const scaleIndex = viewScales.indexOf(scale)
  return (
    <Modal onClose={onClose} label="Adjust Mission Control view" className="modal--view">
      <div className="view-panel">
        <span className="eyebrow"><Monitor size={13} /> DISPLAY CONTROL</span>
        <h2>Fit the control room to you.</h2>
        <p>These settings change only this browser. They do not alter workspace data or another user’s view.</p>
        <section className="view-control">
          <div><span>INTERFACE SIZE</span><strong>{scale}%</strong></div>
          <div className="view-stepper">
            <button type="button" onClick={() => onScale(viewScales[Math.max(0, scaleIndex - 1)])} disabled={scaleIndex === 0} aria-label="Make interface smaller"><Minus size={16} /></button>
            <input type="range" min="80" max="120" step="10" value={scale} onChange={(event) => onScale(Number(event.target.value) as ViewScale)} aria-label="Interface size" />
            <button type="button" onClick={() => onScale(viewScales[Math.min(viewScales.length - 1, scaleIndex + 1)])} disabled={scaleIndex === viewScales.length - 1} aria-label="Make interface larger"><Plus size={16} /></button>
          </div>
          <div className="view-scale-labels"><span>More space</span><span>Default</span><span>Larger text</span></div>
        </section>
        <section className="view-control">
          <div><span>INFORMATION DENSITY</span><strong>{density === 'compact' ? 'COMPACT' : 'COMFORTABLE'}</strong></div>
          <div className="density-switch" role="group" aria-label="Information density">
            <button type="button" className={density === 'comfortable' ? 'is-active' : ''} onClick={() => onDensity('comfortable')}>Comfortable<small>More breathing room</small></button>
            <button type="button" className={density === 'compact' ? 'is-active' : ''} onClick={() => onDensity('compact')}>Compact<small>More data at once</small></button>
          </div>
        </section>
        <div className="view-panel__actions">
          <button type="button" className="button button--quiet" onClick={onFullscreen}><Maximize2 size={15} />{fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}</button>
          <button type="button" className="button button--quiet" onClick={onReset}><RotateCcw size={15} />Reset view</button>
        </div>
        <div className="view-shortcuts"><span>KEYBOARD</span><div><kbd>Ctrl</kbd><b>K</b><span>Commands</span><kbd>?</kbd><b>—</b><span>Guide</span></div><p>Browser zoom shortcuts remain controlled by your browser.</p></div>
      </div>
    </Modal>
  )
}

function CommandDeck({ setView, runGate, onClose, busy, controlsEnabled }: { setView: (view: View) => void; runGate: (id: string) => void; onClose: () => void; busy: boolean; controlsEnabled: boolean }) {
  const go = (view: View) => { setView(view); onClose() }
  return (
    <Modal onClose={onClose} label="Command deck">
      <div className="command-deck">
        <span className="eyebrow"><Command size={13} /> OPERATOR COMMAND DECK</span>
        <h2>What do you need to prove?</h2>
        <div className="command-list">
          <button type="button" onClick={() => go('engagements')}><Target size={17} /><span><strong>Open engagement workspace</strong><small>Scope a site, build, client or repeat assessment</small></span><kbd>00</kbd></button>
          <button type="button" disabled={busy || !controlsEnabled} onClick={() => { runGate('all'); onClose() }}><Play size={17} /><span><strong>{controlsEnabled ? 'Run all engineering gates' : 'Controls unavailable in demo'}</strong><small>{controlsEnabled ? 'Execute the authoritative manifest' : 'Use the private operator console'}</small></span><kbd>01</kbd></button>
          <button type="button" onClick={() => go('gates')}><ShieldCheck size={17} /><span><strong>Open verification matrix</strong><small>Run or inspect individual gates</small></span><kbd>02</kbd></button>
          <button type="button" onClick={() => go('agents')}><Bot size={17} /><span><strong>Inspect active agents</strong><small>See bounded local journal status</small></span><kbd>03</kbd></button>
          <button type="button" onClick={() => go('evidence')}><Fingerprint size={17} /><span><strong>Verify evidence chains</strong><small>Readiness and action provenance</small></span><kbd>04</kbd></button>
          <button type="button" onClick={() => go('shadow')}><ShieldAlert size={17} /><span><strong>Open Shadow AI defense</strong><small>Inventory, policy, egress, and violations</small></span><kbd>05</kbd></button>
          <button type="button" onClick={() => go('coverage')}><ScanSearch size={17} /><span><strong>Inspect security coverage</strong><small>Seven-team ownership and telemetry gaps</small></span><kbd>06</kbd></button>
        </div>
      </div>
    </Modal>
  )
}

function Loading({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  return (
    <main className="loading-screen">
      <Logo />
      <div className="loading-scan"><i /></div>
      <h1>{error ? 'CONTROL PLANE UNAVAILABLE' : 'ESTABLISHING TRUST CHANNEL'}</h1>
      <p className="loading-message" role="status" aria-live="polite" aria-atomic="true">
        {error ? '' : 'Reading authoritative manifests…'}
      </p>
      <p className="loading-message" role="alert" aria-live="assertive" aria-atomic="true">
        {error ?? ''}
      </p>
      {error && <button type="button" className="loading-retry" onClick={onRetry}><RefreshCw size={14} /> Retry secure connection</button>}
    </main>
  )
}

export default function App() {
  const { snapshot, engagements, connected, error, retryInitial, runGate, refresh, decideTask, decideAsset, decideViolation, updateShadowPolicy, updateRetention, updateSafety, provisionConnector, createEngagement, uploadEngagementAssets, launchEngagement, analyzeEngagementAsset, compareEngagementRuns, engagementExportUrl, evidenceDownloadUrl } = useMissionControl()
  const [view, setViewState] = useState<View>(viewFromLocation)
  const [commandOpen, setCommandOpen] = useState(false)
  const [assuranceOpen, setAssuranceOpen] = useState(false)
  const [policyOpen, setPolicyOpen] = useState(false)
  const [retentionOpen, setRetentionOpen] = useState(false)
  const [safetyOpen, setSafetyOpen] = useState(false)
  const [connectorOpen, setConnectorOpen] = useState(false)
  const [engagementOpen, setEngagementOpen] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [viewSettingsOpen, setViewSettingsOpen] = useState(false)
  const [viewScale, setViewScale] = useState<ViewScale>(() => {
    try {
      const stored = Number(window.localStorage.getItem('aegis.view.scale')) as ViewScale
      return viewScales.includes(stored) ? stored : 100
    } catch {
      return 100
    }
  })
  const [viewDensity, setViewDensity] = useState<ViewDensity>(() => {
    try {
      return window.localStorage.getItem('aegis.view.density') === 'compact' ? 'compact' : 'comfortable'
    } catch {
      return 'comfortable'
    }
  })
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement))
  const [toast, setToast] = useState<{ tone: 'ok' | 'error'; message: string } | null>(null)
  const busy = useMemo(() => snapshot?.runs.some((run) => run.status === 'queued' || run.status === 'running') ?? false, [snapshot?.runs])

  const setView = (next: View) => {
    const nextHash = viewHash[next]
    if (window.location.hash !== nextHash) window.history.pushState({ aegisView: next }, '', nextHash)
    setViewState(next)
  }

  useEffect(() => {
    const syncView = () => setViewState(viewFromLocation())
    window.addEventListener('popstate', syncView)
    window.addEventListener('hashchange', syncView)
    return () => {
      window.removeEventListener('popstate', syncView)
      window.removeEventListener('hashchange', syncView)
    }
  }, [])

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
      document.querySelector<HTMLElement>('.app-content [data-view-heading]')?.focus({ preventScroll: true })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [view])

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const editing = Boolean(target?.closest('input, textarea, select, [contenteditable="true"]'))
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen((current) => !current)
        return
      }
      if (!editing && event.key === '?') {
        event.preventDefault()
        setGuideOpen(true)
        return
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem('aegis.view.scale', String(viewScale))
      window.localStorage.setItem('aegis.view.density', viewDensity)
    } catch {
      // Browser privacy settings may intentionally disable persistent preferences.
    }
  }, [viewDensity, viewScale])

  useEffect(() => {
    const changed = () => setFullscreen(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', changed)
    return () => document.removeEventListener('fullscreenchange', changed)
  }, [])

  useEffect(() => {
    if (!snapshot) return
    try {
      const key = `aegis.guide.seen.${guideVersion}.${snapshot.deployment.mode}`
      if (window.localStorage.getItem(key) !== '1') setGuideOpen(true)
    } catch {
      setGuideOpen(true)
    }
  }, [snapshot?.deployment.mode])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 4200)
    return () => window.clearTimeout(timer)
  }, [toast])

  if (!snapshot) return <Loading error={error} onRetry={retryInitial} />
  const controlsEnabled = snapshot.deployment.controlsEnabled

  const closeGuide = () => {
    try {
      window.localStorage.setItem(`aegis.guide.seen.${guideVersion}.${snapshot.deployment.mode}`, '1')
    } catch {
      // The guide remains available from the header when preferences cannot persist.
    }
    setGuideOpen(false)
  }

  const toggleFullscreen = () => {
    const action = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()
    void action.catch(() => setToast({ tone: 'error', message: 'Fullscreen is unavailable in this browser window.' }))
  }

  const execute = (gateId: string, mode: 'engineering' | 'assurance' = 'engineering') => {
    if (!controlsEnabled) {
      setToast({ tone: 'error', message: 'Public demo mode is read-only. Open the private operator console to run controls.' })
      return
    }
    void runGate(gateId, mode)
      .then((run) => {
        setToast({ tone: 'ok', message: `${run.gateName} accepted by the command bus` })
        setView('gates')
      })
      .catch((reason: unknown) => setToast({ tone: 'error', message: reason instanceof Error ? reason.message : 'Run request failed' }))
  }

  const control = (promise: Promise<void>, success: string) => {
    void promise
      .then(() => setToast({ tone: 'ok', message: success }))
      .catch((reason: unknown) => setToast({ tone: 'error', message: reason instanceof Error ? reason.message : 'Control request failed' }))
  }

  return (
    <div className="app-shell" data-density={viewDensity} style={{ '--view-scale': viewScale / 100 } as CSSProperties}>
      <NavRail view={view} setView={setView} />
      <div className="app-stage">
        <TopBar snapshot={snapshot} connected={connected} onCommand={() => setCommandOpen(true)} onGuide={() => setGuideOpen(true)} onViewSettings={() => setViewSettingsOpen(true)} viewScale={viewScale} />
        <MarkingBar snapshot={snapshot} />
        <main className="app-content">
          {view === 'overview' && <Overview snapshot={snapshot} runGate={execute} setView={setView} busy={busy} controlsEnabled={controlsEnabled} />}
          {view === 'engagements' && <EngagementsView snapshot={snapshot} engagements={engagements} controlsEnabled={controlsEnabled} onNew={() => setEngagementOpen(true)} onUpload={uploadEngagementAssets} onLaunch={launchEngagement} onAnalyze={analyzeEngagementAsset} onCompare={compareEngagementRuns} onOpenWorkspace={() => setView('workspace')} engagementExportUrl={engagementExportUrl} evidenceDownloadUrl={evidenceDownloadUrl} />}
          {view === 'coverage' && <CoverageView snapshot={snapshot} />}
          {view === 'shadow' && <ShadowAIView snapshot={snapshot} controlsEnabled={controlsEnabled} onAssetDecision={(assetId, disposition) => control(decideAsset(assetId, disposition), `AI asset marked ${disposition}`)} onViolationDecision={(violationId, status) => control(decideViolation(violationId, status), `Violation ${status}`)} onEditPolicy={() => setPolicyOpen(true)} />}
          {view === 'teams' && <TeamsView snapshot={snapshot} runGate={execute} busy={busy} controlsEnabled={controlsEnabled} />}
          {view === 'gates' && <GatesView snapshot={snapshot} runGate={execute} busy={busy} onAssurance={() => setAssuranceOpen(true)} controlsEnabled={controlsEnabled} />}
          {view === 'agents' && <AgentsView snapshot={snapshot} />}
          {view === 'workspace' && <WorkspaceView snapshot={snapshot} controlsEnabled={controlsEnabled} onTaskDecision={(taskId, decision) => control(decideTask(taskId, decision), `Task ${decision}`)} onEditRetention={() => setRetentionOpen(true)} onEditSafety={() => setSafetyOpen(true)} onProvisionConnector={() => setConnectorOpen(true)} />}
          {view === 'evidence' && <EvidenceView snapshot={snapshot} />}
        </main>
        <footer className="footer-line">
          <span>AEGIS CONTROL PLANE v1.0 / {snapshot.deployment.mode.toUpperCase()}</span><i />
          <span>DOCSET {snapshot.program.documentVersion}</span><i />
          <button type="button" onClick={() => void refresh()}><RefreshCw size={11} /> SYNC {shortTime(snapshot.generatedAt)}</button>
          <span className="footer-line__right">{snapshot.deployment.mode === 'saas' ? 'TENANT ISOLATED' : snapshot.deployment.mode === 'demo' ? 'SYNTHETIC ONLY' : 'LOOPBACK'} / AUDIT {snapshot.controlLedger.ok ? 'VERIFIED' : 'FAULT'}</span>
        </footer>
      </div>
      {guideOpen && <GuidePanel snapshot={snapshot} setView={setView} onClose={closeGuide} />}
      {viewSettingsOpen && <ViewPanel scale={viewScale} density={viewDensity} fullscreen={fullscreen} onScale={setViewScale} onDensity={setViewDensity} onFullscreen={toggleFullscreen} onReset={() => { setViewScale(100); setViewDensity('comfortable') }} onClose={() => setViewSettingsOpen(false)} />}
      {commandOpen && <CommandDeck setView={setView} runGate={execute} onClose={() => setCommandOpen(false)} busy={busy} controlsEnabled={controlsEnabled} />}
      {assuranceOpen && (
        <Modal onClose={() => setAssuranceOpen(false)} label="Confirm fail-closed readiness check">
          <div className="confirm-dialog">
            <div className="confirm-dialog__icon"><CircleStop size={28} /></div>
            <span className="eyebrow">FAIL-CLOSED PATH</span>
            <h2>Run the readiness gate?</h2>
            <p>This check is expected to fail while human-controlled prerequisites remain pending. Failure preserves the program hold; it does not mean the engineering system is broken.</p>
            <div className="confirm-dialog__warning"><AlertTriangle size={16} /><span>Results remain {snapshot.program.marking}</span></div>
            <div className="confirm-dialog__actions"><button type="button" className="button button--quiet" onClick={() => setAssuranceOpen(false)}>Cancel</button><button type="button" className="button button--danger" onClick={() => { execute('readiness', 'assurance'); setAssuranceOpen(false) }}><LockKeyhole size={15} /> Run fail-closed check</button></div>
          </div>
        </Modal>
      )}
      {policyOpen && snapshot.platform?.shadowAI && <PolicyEditor policy={snapshot.platform.shadowAI.policy} onClose={() => setPolicyOpen(false)} onSave={(policy) => { control(updateShadowPolicy(policy), 'Shadow AI policy updated'); setPolicyOpen(false) }} />}
      {retentionOpen && snapshot.platform && <RetentionEditor retention={snapshot.platform.retention} onClose={() => setRetentionOpen(false)} onSave={(retention) => { control(updateRetention(retention), 'Retention policy updated'); setRetentionOpen(false) }} />}
      {safetyOpen && snapshot.platform && <SafetyEditor current={snapshot.platform.workspace.safetyLevel} onClose={() => setSafetyOpen(false)} onSave={(level, reason) => { control(updateSafety(level, reason), `Safety state changed to ${level}`); setSafetyOpen(false) }} />}
      {connectorOpen && <ConnectorEditor onClose={() => setConnectorOpen(false)} onProvision={provisionConnector} />}
      {engagementOpen && <EngagementEditor onClose={() => setEngagementOpen(false)} onCreate={async (input) => { const engagement = await createEngagement(input); setEngagementOpen(false); setView('engagements'); setToast({ tone: 'ok', message: `${engagement.name} is ready for secure intake.` }) }} />}
      {toast && <div className={`toast is-${toast.tone}`}><span>{toast.tone === 'ok' ? <Check size={15} /> : <AlertTriangle size={15} />}</span>{toast.message}<button type="button" onClick={() => setToast(null)}><X size={14} /></button></div>}
    </div>
  )
}
