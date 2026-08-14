<!-- Copy as INC-YYYY-NNNN.md. Spec: ../ARTIFACTS.md · Lifecycle: ../docs/INCIDENT_RESPONSE.md -->
# Incident INC-YYYY-NNNN

Severity:                 critical | high | medium | low
Declared at / by:         <UTC> / <named human>
Incident commander:       |  Scribe / evidence owner:
Comms channel:            |  Systems / identities:
Business impact:          <in the owner's terms>

## Evidence preservation
Preserved BEFORE destructive action:  what | when | acquisition method
<!-- If containment happened first, SAY SO PLAINLY. Do not backfill. -->

## Validation
CONFIRMED:
BELIEVED:
ESTIMATED:
UNKNOWN:      <- a DECLARED unknown is an acceptable closure state. A silent one is not.

## Scope
identities | hosts | cloud resources | network | persistence | data access | recovery systems

## Containment
| Action | Risk | Approver 1 | Approver 2 (if high-risk) | Expected impact | Success signal | Rollback | Executed | Result |
|---|---|---|---|---|---|---|---|---|

## Eradication
persistence removed | exposure closed | secrets rotated | controls restored | alternate access hunted

## Recovery
Restored from:            |  Integrity validated how:
Monitoring elevated until: |  **Business-owner acceptance: <name> <date>**

## Timing   -> feeds M-5 (MTTI), M-6 (MTTC)
first activity | first signal | acknowledged | investigated | contained | recovered
<!-- Measure from the ADVERSARY ACTION, not from the alert. Containing 20 minutes after an
     alert that fired 6 hours late is not a 20-minute response. -->

## Closure gate (B14) — all required
[ ] Scope established
[ ] Cause established OR unknown explicitly declared
[ ] Containment evidence attached
[ ] Recovery validated and accepted
[ ] Lessons recorded with owners and dates
[ ] Detection/prevention follow-up raised to Green / Yellow / Orange
[ ] Emulation-conversion review scheduled with Purple (within 30 days)
[ ] WhyCase created (trigger W-2) — see ../../00-shared/15_why_engine_and_soul_integration.md
