# §6 — Communication Protocol

← [Index](../README.md) · Prev → [§5 RoE](04_rules_of_engagement_template.md) · Next → [§7 Artifacts](06_artifact_index_and_standards.md)

---

## 6.1 Channel architecture

| # | Channel | Purpose | Members | Retention | Classification ceiling | Label |
|---|---|---|---|---|---|---|
| C1 | `#sec-purple-general` | Day-to-day coordination, scheduling, non-sensitive Q&A | All five teams, SOC, CTI | 1 year | INTERNAL | [M] |
| C2 | `#ex-<ID>-ops` | Live exercise coordination. **One channel per exercise, archived at close.** | Named participants only, per RoE | 7 years (exported to evidence store) | Per RoE §5.0 | [M] |
| C3 | `#ex-<ID>-white` **RESTRICTED** | White-only: authorization status, stop deliberation, scoring, answer key, blind-phase control | White Cell only + designated Legal/Privacy | 7 years | Per RoE, often higher | [M] |
| C4 | `#ex-<ID>-deconflict` | "Is this us?" queries, 5-minute SLA | SOC lead, CSIRT commander, deconfliction contact, White, Purple Lead | 7 years | INTERNAL | [M] |
| C5 | Incident bridge (existing IR channel/conference) | **Real** incident response. **Never used for exercise chatter.** | Per IR plan | Per IR plan | Per IR plan | [M] |
| C6 | Out-of-band: phone tree + non-corporate messaging | Used when corporate comms are degraded or when the exercise may have affected them | White + all leads + System Owners | Call log retained | Voice only; no artifacts | [M] |
| C7 | `#sec-detections` | Green ↔ SOC ↔ Purple detection engineering | Green, SOC, Purple | 1 year | INTERNAL | [R] |
| C8 | `#sec-design-review` | Orange ↔ Yellow design and threat-model queue | Orange, Yellow, architects | 1 year | INTERNAL | [R] |
| C9 | Executive briefing (scheduled, not a channel) | Quarterly metrics and AAR summaries | Exec, CISO, White | 7 years | INTERNAL/CONFIDENTIAL | [M] |

### Rules that make the architecture work
- **[M] C3 is genuinely restricted.** Access list reviewed by the Exercise Director before each
  exercise. If a participant can read the White channel, White has no information boundary and
  blind phases are impossible.
- **[M] C5 is never used for exercise traffic.** The moment exercise chatter appears on the real
  incident bridge, the organization loses the ability to distinguish drills from reality under
  stress — which is precisely when it matters.
- **[M] C2 is created per-exercise and archived to evidence at close.** Persistent "purple team"
  channels lose the chronology that the AAR and any subsequent legal review depend on.
- **[M] No exercise details in DMs.** If it is not in a channel, it did not happen — and it
  cannot be evidenced. This is a common failure and it is worth stating repeatedly.
- **[R] Bots that post automated exercise events into C2** (see §6.4) reduce transcription
  errors and give the AAR a reliable timeline for free.

---

## 6.2 Meeting cadence

| Meeting | Frequency | Duration | Chair | Required | Output |
|---|---|---|---|---|---|
| Threat-informed prioritization | Monthly | 60 min | Purple Lead | Purple, CTI, SOC, Orange, GRC | Ranked scenario candidates |
| Exercise Review Board | Monthly | 60 min | White Exercise Director | White, Purple, System Owners, Legal (async ok) | Approve/deny RoEs |
| Pre-exercise brief | T-2 days | 45 min | Purple Lead | All participants + White | Confirm readiness; test contacts live |
| Daily exercise sync (during execution) | Daily 09:00 + 17:00 | 15 min | Purple Lead | Operators, White, SOC lead, Ops | Status, blockers, safety check |
| Collaborative validation session | End of execution | 4–8 h | Purple Lead | Purple, Red, Blue, Green, Orange, scribe | Six-stage outcomes with evidence |
| Hot wash | Within 24 h of end | 60 min | White | All participants | Immediate observations, before memory decays |
| Formal AAR review | ≤10 business days | 90 min | White | All + System Owners + exec optional | Published AAR |
| Detection backlog grooming | Bi-weekly | 45 min | Green Lead | Green, SOC, Purple | Prioritized detection work |
| Remediation standup | Weekly | 15 min | Yellow eng manager | Yellow, Purple findings owner | Ticket status |
| Retest batch | Bi-weekly | 2 h | Purple | Purple, Green, Yellow | Retest records |
| Design review clinic | Weekly office hours | 60 min | Orange Lead | Orange + any Yellow team | Threat models, abuse cases |
| Metrics review (ops) | Monthly | 45 min | Purple Lead | All leads | Metric pack + decisions |
| Metrics review (exec) | Quarterly | 30 min | CISO | Exec, White | Trend decisions, budget |
| White independence review | Annual | 2 h | Internal Audit | White | Independence attestation |

---

## 6.3 Daily exercise update format

Posted to C2 at 09:00 and 17:00 local during any execution window. **[M]** — a day without an
update is a day without a record.

```
EXERCISE DAILY UPDATE -- EX-2026-014 -- Day 2 of 4 -- 2026-09-16T17:00Z

STATUS:            GREEN | AMBER | RED     (RED = stopped)
SAFETY:            No safety events | <describe>
TEST CASES:        Executed 7 / Planned 12 | Deferred 1 (TC-009: pre-prod unavailable)
SIX-STAGE SUMMARY: prevented 2 | logged 6 | alerted 3 | investigated 2 | contained 1 | reported 1
STOPS:             0 | <list with times and outcomes>
DECONFLICTION:     2 queries, both resolved <5 min
FINDINGS (prelim): 1 High, 2 Medium  (IDs only; detail in the record, not in chat)
SCOPE CHANGES:     None | <White approval reference>
BLOCKERS:          <what, who is needed, by when>
NEXT 24H:          TC-010 through TC-012, window 09:00-15:00
CONTACT CHECK:     All required roles confirmed reachable  ☐ yes ☐ no -> escalate
```

**Status definitions [M]:** GREEN = proceeding as planned · AMBER = deviation, ongoing, White
informed · RED = stopped, awaiting White decision. AMBER and RED both require a White
acknowledgement post in the same channel.

---

## 6.4 Machine-readable formats

Emit these as JSON to the case management system and the evidence store. **Rationale:** if
findings and events are only prose, metrics in §8 must be hand-counted, which means they will be
produced late, inconsistently, or not at all.

> Conventions: all timestamps RFC 3339 UTC · all IDs stable and immutable · `schema_version`
> present on every object · unknown fields rejected, not ignored.

### 6.4.1 Exercise event (streamed during execution)
```json
{
  "schema_version": "1.0",
  "event_id": "EVT-2026-014-0031",
  "exercise_id": "EX-2026-014",
  "timestamp": "2026-09-16T14:22:07Z",
  "event_type": "test_case_executed",
  "actor": {
    "type": "operator",
    "identity": "svc-ex-2026-014-03",
    "human": "j.doe",
    "source_ip": "10.44.7.19"
  },
  "test_case_id": "TC-2026-014-007",
  "attack": {
    "tactic": "TA0006",
    "technique": "T1110.003",
    "technique_name": "Password Spraying",
    "sub_technique": true
  },
  "target": {
    "asset_id": "ASSET-0442",
    "environment": "pre-prod",
    "in_scope_ref": "ROE-2026-014 sec 5.3 row 2"
  },
  "expected_telemetry": ["EntraID:SignInLogs", "EDR:ProcessCreate"],
  "expected_detection": ["DET-0198"],
  "outcome": "executed",
  "blast_radius": "single-tenant test accounts only",
  "evidence_refs": ["EV-2026-014-0088"],
  "roe_ref": "ROE-2026-014",
  "deconfliction_marker": "EX-2026-014",
  "notes": "Executed 12 attempts across 40 accounts over 20 minutes."
}
```
`event_type` enum: `exercise_started` · `test_case_executed` · `detection_observed` ·
`alert_triaged` · `containment_action` · `stop_called` · `stop_resolved` · `scope_change` ·
`deconfliction_query` · `evidence_captured` · `exercise_ended`

### 6.4.2 Finding
```json
{
  "schema_version": "1.0",
  "finding_id": "FND-2026-0143",
  "exercise_id": "EX-2026-014",
  "created": "2026-09-18T10:05:00Z",
  "title": "Password spraying against Entra ID produces no alert below 15 attempts/account/hour",
  "type": "detection_gap",
  "severity": "high",
  "severity_rationale": {
    "exploitability": "high",
    "impact": "high",
    "exposure": "internet-facing",
    "compensating_controls": ["conditional access blocks legacy auth"],
    "rubric_version": "1.2"
  },
  "affected_assets": ["ASSET-0442", "ASSET-0443"],
  "attack_mapping": [{"technique": "T1110.003", "tactic": "TA0006"}],
  "six_stage_outcome": {
    "prevented": "not_blocked",
    "logged": "full",
    "alerted": "no_alert",
    "investigated": "not_triaged",
    "contained": "no",
    "reported": "no"
  },
  "evidence_refs": ["EV-2026-014-0088", "EV-2026-014-0091"],
  "acceptance_criteria": [
    "Detection fires within 15 min for >=10 failed auths across >=5 distinct accounts from one source in 1 hour",
    "Alert routes to SOC queue with severity >= medium",
    "Purple re-executes TC-2026-014-007 verbatim and observes alert"
  ],
  "remediation_owner": "a.smith",
  "system_owner": "m.chen",
  "target_date": "2026-10-18",
  "status": "open",
  "linked_tickets": ["SEC-4471"],
  "classification": "INTERNAL",
  "regression_test_id": null
}
```
`type` enum: `vulnerability` · `detection_gap` · `control_gap` · `process_gap` ·
`telemetry_gap` · `response_gap`
`status` enum: `open` · `in_remediation` · `awaiting_retest` · `closed` · `risk_accepted` ·
`regressed`

### 6.4.3 Detection gap → detection request
```json
{
  "schema_version": "1.0",
  "gap_id": "GAP-2026-0087",
  "source_finding": "FND-2026-0143",
  "attack_mapping": [{"technique": "T1110.003"}],
  "required_data_sources": ["EntraID:SignInLogs"],
  "data_source_available": true,
  "telemetry_gap": false,
  "proposed_logic_summary": "Threshold + distinct-account cardinality per source IP per hour",
  "expected_false_positive_drivers": ["misconfigured mail clients", "shared NAT egress"],
  "priority": "P2",
  "assigned_to": "green-team",
  "target_deploy": "2026-10-02",
  "detection_id": null,
  "validated_by_purple": false
}
```

### 6.4.4 Retest record
```json
{
  "schema_version": "1.0",
  "retest_id": "RT-2026-0091",
  "finding_id": "FND-2026-0143",
  "test_case_id": "TC-2026-014-007",
  "procedure_identical_to_original": true,
  "retest_date": "2026-10-21T13:00:00Z",
  "performed_by": "purple",
  "original_outcome": {"alerted": "no_alert", "investigated": "not_triaged"},
  "retest_outcome": {"alerted": "alerted", "detection_id": "DET-0231", "investigated": "correct"},
  "time_to_detect_seconds": 412,
  "verdict": "closed",
  "evidence_refs": ["EV-2026-014-0140"],
  "regression_test_added": true,
  "regression_test_id": "REG-0055"
}
```
`verdict` enum: `closed` · `partially_remediated` · `not_remediated` · `regressed`

### 6.4.5 Stop event
```json
{
  "schema_version": "1.0",
  "stop_id": "STOP-2026-014-002",
  "exercise_id": "EX-2026-014",
  "called_by": "soc.analyst.k",
  "called_at": "2026-09-17T11:14:33Z",
  "reason_category": "suspected_real_incident",
  "reason_text": "Auth failures from an IP not on the exercise allow-list",
  "activity_halted_at": "2026-09-17T11:15:02Z",
  "white_assessment": "unrelated_real_activity_confirmed_benign",
  "decision": "resume_with_conditions",
  "conditions": ["Add source to deconfliction watch", "Re-brief SOC on allow-list"],
  "decided_by": "white.exercise.director",
  "decided_at": "2026-09-17T12:02:10Z",
  "downtime_minutes": 47,
  "included_in_aar": true
}
```
`reason_category` enum: `safety` · `outage` · `data_exposure` · `suspected_real_incident` ·
`loss_of_control` · `third_party_impact` · `legal_concern` · `role_unavailable` ·
`objective_met` · `precautionary`

**[M] Every stop event is recorded and appears in the AAR, including stops later determined to
be unnecessary.** Suppressing "false" stops is how a program teaches people not to call them.

---

## 6.5 Decision logging

**[M] Every decision that changes scope, safety, severity, or status is logged** — in the
channel *and* in the record.

| Field | Required |
|---|---|
| Decision ID | ✓ |
| Timestamp (UTC) | ✓ |
| Decision maker (named human — never "the team", never an AI agent) | ✓ |
| Decision | ✓ |
| Options considered | ✓ |
| Rationale | ✓ |
| Who was consulted | ✓ |
| Reversibility / rollback | ✓ |
| Recorded in | ✓ |

Inline chat format for speed:
```
DECISION EX-2026-014-D07 | 2026-09-17T12:02Z | white.exercise.director
DECIDED: Resume with conditions after STOP-002
OPTIONS: (a) terminate (b) resume as-is (c) resume with conditions
WHY:     Activity confirmed unrelated and benign; exercise objectives not yet met;
         added monitoring reduces recurrence risk
CONSULTED: SOC lead, Purple lead, System owner (ASSET-0442)
REVERSIBLE: yes -- stop again at any time
```

---

## 6.6 Shift handoffs

Required whenever an exercise spans shifts or an on-call rotation boundary. **[M]** for any
exercise longer than one working day.

```
HANDOFF -- EX-2026-014 -- outgoing j.doe -> incoming r.patel -- 2026-09-16T17:00Z

CURRENT STATE:     Status GREEN. No active test activity. All tooling idle.
COMPLETED:         TC-001..TC-007
IN FLIGHT:         None  (or: TC-008 partial, stopped at step 3, state preserved at <ref>)
NEXT PLANNED:      TC-008..TC-010, window opens 09:00 local
OPEN STOPS:        None
ACTIVE IDENTITIES: svc-ex-2026-014-01, -03 (expire 2026-09-19T23:59Z)
LIVE INFRA:        10.44.7.19 (registered), lab-vm-07
UNCLEANED ARTIFACT
S:                 test file /tmp/ex014-marker.txt on host X -- scheduled removal at close
WATCH ITEMS:       SOC investigating unrelated alert on ASSET-0501 -- not ours, confirmed
CONTACTS VERIFIED: White (yes), System Owner (yes), Ops on-call (yes -- new person, r.kim)
INCOMING ACK:      r.patel confirms read + understood at 17:04Z
```

**[M] No handoff without an explicit acknowledgement from the incoming person.** Unacknowledged
handoffs are where uncleaned artifacts and orphaned identities come from.

---

## 6.7 Rules for disclosing test details

| Audience | What they get | When | Rationale |
|---|---|---|---|
| **Defenders (SOC/Blue) — collaborative mode** | **Everything**: technique, timing, source, identity, expected telemetry | Real time | Collaborative validation is a *teaching* exercise. Withholding wastes the most expensive part of the program. |
| **Defenders — designated blind phase** | Nothing until the phase ends | Phase end, then full disclosure | Only with a White-designated phase, a stated learning objective, and a defined end time |
| **Engineering (Yellow)** | Findings affecting their systems, with reproduction detail | At classification (stage 10) | They need reproduction detail to fix it |
| **System Owners** | Full findings for their systems + business impact | At classification | They accept the risk; they need the whole picture |
| **Executives** | AAR summary, score, trends, decisions needed | At AAR publication | Not raw technique detail; they need decisions |
| **Broader workforce** | Sanitized lessons, no system identifiers | Post-AAR | Awareness value without creating a target map |
| **External / customers / regulators** | **Nothing without Legal approval** | Per Legal | Findings may be privileged and are often contractually restricted |
| **Auditors / assessors** | Evidence per the crosswalk, through GRC | On request | Controlled channel reduces accidental over-disclosure |
| **Vendors / providers** | Only findings in their layer, via coordinated disclosure | Per §5.15 | |

**Standing rules [M]:**
- Blind is the exception and must be justified in writing. Default is transparent.
- Disclosure inside a blind phase, however well-intentioned, ends the phase — report it to White
  rather than pretending it did not happen.
- Never disclose exercise details in a channel that is not on the RoE distribution list.
- Never place findings, evidence, credentials, or CUI into a general-purpose AI tool. Approved
  AI agents (see [§10](09_ai_and_automation_governance.md)) have explicit data-classification
  limits; consumer tools have none.

---

## 6.8 Distinguishing test activity from a real compromise

This is the operational core of the whole communication protocol. Four layers, defense in depth:

| Layer | Mechanism | Owner | Label |
|---|---|---|---|
| **1 — Pre-registration** | Source IPs, hostnames, identities, tool signatures, and the exercise marker registered before start and provided to SOC leadership | White | [M] |
| **2 — Marking** | Every exercise identity, artifact, filename, and user-agent carries the exercise ID | Purple | [M] |
| **3 — Live deconfliction** | Dedicated channel, named contact, **5-minute response SLA**, 24×7 during the window | White + Purple | [M] |
| **4 — Answer key** | White holds the authoritative activity log and can confirm or deny any specific action | White | [M] |

### The deconfliction decision tree
```
SOC observes suspicious activity
        |
        v
Does it match a pre-registered indicator (layer 1/2)?
        |-- YES --> Log as exercise. CONTINUE PRACTICING THE RESPONSE.
        |            Suppress ONLY external notification and destructive containment.
        |            Record the deconfliction (feeds MTTD metrics).
        |
        +-- NO ---> Query the deconfliction channel (layer 3). SLA 5 min.
                       |-- "EXERCISE" ------> as above
                       |-- "NOT EXERCISE" --> DECLARE REAL INCIDENT. Full IR. White notified;
                       |                      White decides whether to stop the exercise.
                       +-- "UNKNOWN" or no response in 5 min
                                            --> TREAT AS REAL. Full IR. Escalate to White in
                                                parallel. Never wait on deconfliction.
```

**[M] The default on ambiguity is always "real."** The cost asymmetry is not close: a wasted IR
activation costs a few hours; a real intrusion dismissed as "probably the purple team" is a
breach. Write this rule into the IR plan itself, not just into the exercise documentation — the
analyst at 03:00 will read the IR plan.

### Protecting the exercise without compromising safety
Deconfliction inevitably leaks some information to the querying analyst. Mitigate by:
- Answering only the **specific** query ("that IP at that time: yes, exercise") — never
  volunteering the plan
- Routing queries through the SOC **lead**, not every analyst
- Recording every deconfliction query as an exercise event (it is itself a detection signal:
  a query means someone noticed, which is a partial success worth scoring)
- Accepting the leak when in doubt. **Exercise fidelity is never worth an unmanaged risk.**
