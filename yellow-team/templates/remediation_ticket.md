<!-- Create in the NORMAL backlog, not a security tracker. Spec: ../ARTIFACTS.md (A8) -->
Title:            <the outcome, not the finding ID>
Finding ref:      FND-YYYY-NNNN
Severity / SLA:   |  Target date:
System owner:     <accountable for it happening>
Assignee:         <named engineer>

## ACCEPTANCE CRITERIA   <- copied VERBATIM from the finding
1.
2.
<!-- If any criterion is not testable, REJECT BACK to Purple before starting work. -->

## Approach
## Blast radius / rollback     <- required for anything touching production
## Regression test             <- ID, or explicit "not automatable because ____"

## Fix evidence
Criterion 1: commit/PR ____ | CI run ____ | verified by ____ (NOT the author - SoD-3)
Criterion 2: config diff ____ | query against <env> at <UTC> returning <result>
Deployment:  env | version | timestamp | change record

Status:  open | in_progress | awaiting_retest | closed
<!-- Only a PASSING RETEST moves this to closed. Not the assignee. -->
