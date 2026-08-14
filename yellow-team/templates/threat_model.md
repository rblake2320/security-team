<!-- Lives WITH THE CODE, versioned. Not on a wiki. Spec: ../ARTIFACTS.md -->
# Threat Model — <system>  TM-<system>-vN

System:               |  System owner:            |  Engineering owner:
Facilitated by:       Orange
Participants:         <the engineers who build it - if they were not in the room, this goes stale>
Date:                 |  Next review due:        <material change, or 12 months>
Criticality tier:

## 1. What are we building?
Components:            |  Data flows:            |  Trust boundaries (mark explicitly):
Data stores:           store | data class | classification | retention
External dependencies: service | data shared | trust assumption
Identities:            human and workload; what each can reach

## 2. What can go wrong?
| Element | Threat | STRIDE | Attack path | Feasibility | Impact | Existing control | Gap |
|---|---|---|---|---|---|---|---|

## 3. What are we doing about it?
| Gap | Decision (mitigate/transfer/accept/eliminate) | Owner | Work item | Due |
|---|---|---|---|---|

## 4. Instrumentation requirements  -> to GREEN
| Path | Required telemetry | Exists today? | Green work item |
|---|---|---|---|

## 5. Abuse cases  -> our backlog as requirements
"As an attacker with <starting position>, I can <action>, because <weakness>."

## 6. AI-specific (where applicable)
Untrusted content entering model context:
Tool/function permissions available to the model:      | approved by:
Model output consumed by downstream systems:           | validation applied:
Tenant / data isolation:                               | prompt-injection mitigations:

## 7. Assumptions and out-of-scope
<- state what you ASSUMED to be secure. Most missed attack paths hide here.

## 8. Review — did we do a good job? What did we skip, and why?

Approved by System Owner: ____________  Date: ______
