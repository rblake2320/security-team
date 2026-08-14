# §7 — Security Artifacts: Index, Standards, and Registry

← [Index](../README.md) · Prev → [§6 Comms](05_communication_protocol.md) · Next → [§8 Metrics](07_metrics.md)

Fill-in templates for each artifact live in the owning team's folder (`*/ARTIFACTS.md`).
This file is the **registry and the standards that apply to all of them**.

---

## 7.1 Artifact registry

| # | Artifact | Owner (author) | Approver | Retention (default) | Marking | System of record | Template |
|---|---|---|---|---|---|---|---|
| A1 | **Exercise Proposal** | Purple Lead | White Exercise Director | 7 years | INTERNAL | Exercise record system | [purple](../purple-team/ARTIFACTS.md) |
| A2 | **Threat Scenario** | Purple + CTI | Purple Lead | 7 years | INTERNAL (CONFIDENTIAL if it names a real actor targeting you) | Exercise record system | [purple](../purple-team/ARTIFACTS.md) |
| A3 | **ATT&CK Technique Test Case** | Purple / Red | Purple Lead + White (safety) | 7 years | INTERNAL | Emulation library (Git) + exercise record | [purple](../purple-team/ARTIFACTS.md) |
| A4 | **Safety Assessment** | Purple (draft) | **White Exercise Director** | 7 years | INTERNAL | Exercise record system | [white](../white-team/ARTIFACTS.md) |
| A5 | **Finding** | Purple | White (adjudicates severity) | 7 years after closure | INTERNAL / CONFIDENTIAL | Case management + backlog | [purple](../purple-team/ARTIFACTS.md) |
| A6 | **Detection Gap** | Purple | Green Lead (accepts into backlog) | 3 years after closure | INTERNAL | Detection backlog (Git/issues) | [purple](../purple-team/ARTIFACTS.md) |
| A7 | **Control Gap** | Purple / Orange | System Owner + GRC | 7 years | INTERNAL | Risk register + GRC platform | [purple](../purple-team/ARTIFACTS.md) |
| A8 | **Engineering Remediation Ticket** | Yellow | System Owner | 3 years after closure | INTERNAL | **Normal engineering backlog** (never a separate security tracker) | [yellow](../yellow-team/ARTIFACTS.md) |
| A9 | **Retest Record** | Purple | Purple Lead | 7 years | INTERNAL | Exercise record + case management | [purple](../purple-team/ARTIFACTS.md) |
| A10 | **Risk Acceptance** | White (routes) | **System Owner signs**; Exec above threshold | 7 years past expiry | CONFIDENTIAL | Risk register (GRC) | [white](../white-team/ARTIFACTS.md) |
| A11 | **Evidence Manifest** | White Evidence Custodian | White Exercise Director | Longest applicable (7 yrs default; 3 yrs FedRAMP/gov contract retention may differ — see O-3/O-16) | Inherits highest content marking | Evidence store (WORM) | [white](../white-team/ARTIFACTS.md) |
| A12 | **After-Action Report** | White Scoring Analyst | **White Exercise Director** (participants may not alter conclusions) | 7 years | INTERNAL / CONFIDENTIAL | Exercise record + exec repository | [white](../white-team/ARTIFACTS.md) |
| A13 | **Lessons-Learned Record** | All participants | System Owner (system lessons) / Purple Lead (program lessons) | 3 years | INTERNAL | Knowledge base + backlog | [purple](../purple-team/ARTIFACTS.md) |

### Supporting artifacts owned outside the 13
| Artifact | Owner | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| Rules of Engagement | White | See RoE §5.18 | 7 years | Per RoE | Exercise record |
| Authorization Record | White | System Owner | 7 years | INTERNAL | Exercise record |
| Threat Model | Yellow + Orange | System Owner | Life of system + 3 years | INTERNAL | Architecture repo (versioned with the code) |
| Abuse/Misuse Case Library | Orange | Orange Lead | Life of system | INTERNAL | Architecture repo |
| Detection content | Green | Green Lead | Life of detection + 3 years | INTERNAL | Detection-as-code repo |
| Telemetry/log source inventory | Green | Green Lead | Current + 3 years | INTERNAL | CMDB / detection repo |
| Defensibility gate record | Green | Green Lead | 3 years | INTERNAL | Release pipeline |
| Restore drill record | Green | Resilience owner | 7 years | INTERNAL | GRC + ops records |
| SBOM / provenance attestation | Yellow | Eng Manager | Life of artifact + 3 years | INTERNAL | Artifact registry |
| Chain of Custody | White | Evidence Custodian | With the evidence | Inherits | Evidence store |
| Destruction Certificate | White | Evidence Custodian + Privacy | 7 years | INTERNAL | Evidence store |
| Decision Log | White (exercise) | Exercise Director | 7 years | Per RoE | Exercise record |
| Scoring Rubric | White | Exercise Director | Version-controlled indefinitely | INTERNAL | Exercise record system |

---

## 7.2 Standards that apply to every artifact **[M]**

### Identification
| Rule | Detail |
|---|---|
| Stable IDs | `<TYPE>-<YYYY>-<NNNN>`. Never reused, never renumbered, never deleted — superseded instead. |
| Traceability | Every artifact links upstream (what caused it) and downstream (what it caused). An artifact with no links is orphaned and will not be found again. |
| Versioning | Semantic-ish: v1.0 → v1.1 (content change) → v2.0 (scope/meaning change). Approved artifacts are re-approved on major version change. |
| Immutability after approval | Approved artifacts are amended by a new version, never edited in place. |

### Marking
| Level | Definition | Handling |
|---|---|---|
| PUBLIC | Releasable | No restriction |
| INTERNAL | Default for this program | Employees + authorized contractors on the distribution list |
| CONFIDENTIAL | Findings on crown jewels, risk acceptances, actor-specific intel | Named access list, encrypted at rest, access logged |
| CUI (+ category) | Where applicable | Marked per the CUI Registry category, stored inside the authorized boundary, never in general-purpose tooling |
| Higher classification | Where applicable | Per the governing security classification guide; **not stored in any system described here unless that system is accredited for it** |

**[M] Marking is inherited from the highest-classified content the artifact contains, including
screenshots and log excerpts.** A screenshot showing a CUI record makes the artifact CUI.

### Retention
| Rule | Detail |
|---|---|
| Default | 7 years, or the longest applicable framework/contract schedule — whichever is greater |
| Regulated overrides | Confirm against O-3/O-16. Do not assume 7 years satisfies every regime; some contracts and record schedules require longer, and some privacy regimes require *shorter* for personal data. |
| Personal data | Shortest retention consistent with the legal obligation; minimize at capture so this conflict rarely arises |
| Legal hold | Overrides all destruction schedules. Legal notifies the Evidence Custodian in writing. |
| Destruction | Scheduled, executed, certified, and logged. Silent expiry is not destruction. |

### Integrity
| Rule | Detail |
|---|---|
| Hashing | SHA-256 at capture, recorded in the manifest before any transfer |
| Timestamps | RFC 3339 UTC, from a synchronized source |
| Custody | Every access and transfer logged |
| Storage | Immutable/WORM for evidence; version-controlled for everything else |
| Prohibited storage | Personal drives, personal devices, personal accounts, unmanaged chat, general-purpose AI tools |

### Quality gates
| Artifact class | Gate |
|---|---|
| Any artifact with an [M] field blank | Not approved. "TBD" is a blank. |
| Finding without evidence references | Rejected — it is an opinion (workflow gate G4) |
| Finding without testable acceptance criteria | Rejected (gate G5) |
| Retest with a modified procedure | Rejected — retest verbatim or record why the original is no longer possible |
| Risk acceptance without an expiry date | Rejected |
| AAR without pre-declared scoring criteria | Rejected — the criteria must predate execution |

---

## 7.3 Field conventions

Shared enumerations used across artifacts, so metrics can be computed without normalization:

```
severity          : critical | high | medium | low | informational
finding_type      : vulnerability | detection_gap | control_gap | process_gap
                    | telemetry_gap | response_gap
status            : open | in_remediation | awaiting_retest | closed
                    | risk_accepted | regressed
environment       : lab | dev | test | pre-prod | prod
six_stage         : prevented | logged | alerted | investigated | contained | reported
outcome_prevented : blocked | partially_blocked | not_blocked | not_applicable
outcome_logged    : full | partial | none
outcome_alerted   : alerted | fired_suppressed | no_alert
outcome_investig. : correct | misclassified | not_triaged
outcome_contained : contained | partial | no
outcome_reported  : yes | late | no
verdict           : closed | partially_remediated | not_remediated | regressed
confidence        : confirmed | probable | possible
```

**[M] Severity rubric inputs are recorded, not just the resulting severity** — exploitability,
impact, exposure, and compensating controls, plus the rubric version. This makes severity
changes auditable and stops quiet downgrades at reporting time.

---

## 7.4 System-of-record principle

> **[M] Do not buy a new system for this program.** Use what the organization already operates:
> the engineering backlog for remediation, the GRC platform for risk and evidence, Git for
> detection and emulation code, the existing case management for exercises. A parallel
> "purple team platform" creates a second source of truth, and the second source of truth is
> always the one nobody updates.

| Data | Lives in | Never lives in |
|---|---|---|
| Remediation work | The delivery team's normal backlog | A security-only spreadsheet |
| Findings | Case management, synced to the backlog | Chat threads, email, a consultant's PDF |
| Evidence | WORM evidence store | Personal drives, screenshots folders |
| Detection content | Git (detection-as-code) | Only inside the SIEM UI |
| Test cases | Git (emulation library) | An operator's laptop |
| Risk acceptance | Risk register | An email chain |
| Threat models | Alongside the code they describe | A wiki page nobody links to |
