# GREEN TEAM — Artifact Templates

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

| Artifact | Approver | Retention | Marking | System of record |
|---|---|---|---|---|
| Detection content (as code) | Green Lead (peer review) | Life of detection + 3 yr | INTERNAL | Detection-as-code repo |
| Detection catalog | Green Lead | Current + 3 yr | INTERNAL | Detection repo (generated) |
| Telemetry / log source inventory | Green Lead | Current + 3 yr | INTERNAL | CMDB / detection repo |
| Hardening baseline + drift report | Green Lead | 3 yr | INTERNAL | Config management |
| Paved-road catalog | Green Lead + Platform | Life of pattern | INTERNAL | Platform repo |
| Defensibility gate record | Green Lead | 3 yr | INTERNAL | Release pipeline |
| SOAR playbook | Green Lead + SOC Manager | Life + 3 yr | INTERNAL | SOAR platform + Git |
| Restore drill record | Resilience owner | 7 yr | INTERNAL | GRC + ops records |
| Control implementation evidence | GRC | Per framework | INTERNAL | GRC platform |

---

## Detection content (detection-as-code)

One file per detection. Version-controlled, peer-reviewed, CI-validated.

```yaml
id: DET-0231                                    # [M] stable, never reused
name: "Credential added to workload identity outside provisioning path"   # [M]
version: 1.2                                    # [M]
status: production                              # [M] draft|testing|production|deprecated
severity: high                                  # [M]
author: g.rivera                                # [M]
peer_reviewed_by: t.osei                        # [M] SoD-1 -- never the author
created: 2026-10-02
deployed_to_production: 2026-10-09T14:00:00Z    # [M] you WILL be asked when this began

attack:                                          # [M]
  - tactic: TA0003
    technique: T1098.001

source_gap: GAP-2026-0087                        # [M] traceability to the finding
source_finding: FND-2026-0143

data_sources:                                    # [M]
  - name: "Directory audit log"
    required_fields: [actor, target_object, credential_type, source_ip, timestamp]
    health_dependency: true      # if this source is down, THIS DETECTION IS DOWN

logic_summary: >                                 # [M] human-readable, behavior not signature
  Credential-addition event on a service/workload identity where the actor is not
  the approved provisioning identity and the change is not linked to an approved
  change record.

query: |                                         # [M] the actual detection logic
  <SIEM query language>

expected_volume_per_week: "0-2"                  # [M] if you cannot estimate, you do not
                                                 #     understand the data yet
expected_fp_drivers:                             # [M] name them BEFORE building
  - "Legitimate emergency credential rotation outside the provisioning path"
  - "Vendor-managed identities with their own lifecycle"

tuning:
  exclusions: []                                 # every exclusion documented and dated
  last_tuned: 2026-11-04
  fp_rate_30d: 0.08

testing:                                         # [M]
  unit_test: tests/det_0231_test.yaml
  fired_in_nonprod: true                         # [M] a detection never observed to fire
  fired_in_nonprod_date: 2026-10-07              #     is a hypothesis, not a detection
  validated_by_purple: true                      # [M] SoD-1
  validated_date: 2026-10-21
  test_case_ref: TC-2026-014-006

response:                                        # [M]
  runbook: runbooks/workload-identity-credential-added.md
  queue: soc-tier2
  automated_actions: []                          # destructive actions require System Owner approval

lifecycle:
  review_due: 2027-10-09                         # [M] annual
  retire_if: "Zero true positives in 12 months AND preventive control deployed"
```

---

## Telemetry / log source inventory

```markdown
# Log Source Inventory   (regenerated weekly)

Source | Owner | Assets covered | Coverage % | Retention hot/cold | Latency target
       | Health (30d) | Detections depending on it | Criticality | Cost/month
-------|-------|----------------|------------|--------------------|---------------

## Health rules  [M]
- Silent > 2x normal max gap        -> page; treat as an outage
- Volume down >50% vs 7-day baseline -> investigate same day
- Below 99% availability in a period -> **every coverage claim for that period
  carries a caveat** (M-10 rule)

## Known gaps  [M]
Source not collected | Why (cost/technical/political) | Detections blocked
                     | Techniques undetectable as a result | Owner | Decision needed by
---------------------|-------------------------------|--------------------

> Name the gaps. A gap you have not written down will be discovered by an
> auditor, or by an adversary.
```

---

## Hardening baseline and drift

```markdown
# Baseline — <platform>   BL-<platform>-vN

Governing benchmark:  [M]  CIS Benchmark vX / DISA STIG vY / vendor guidance
Deviations from benchmark: [M]  setting | our value | benchmark value | justification
                                | approved by | expiry
Applies to:           [M]  asset scope
Enforcement:          [M]  policy-as-code / config management / manual
Drift measurement:    [M]  method + frequency
Last drift report:    [M]  date | assets in scope | assets compliant | top 5 drifted settings
Exceptions:           [M]  asset | setting | reason | risk accepted by | expiry
```

---

## Paved road entry

```markdown
# Paved Road — <name>

Problem it solves:    [M]  the recurring finding class this eliminates
Consumers:            [M]  who should use this
What it provides:     [M]  module/template/base image/pipeline, with the secure
                            defaults it enforces
Security properties:  [M]  what is guaranteed if you use it unmodified
What it does NOT do:  [M]  be explicit -- unstated gaps become assumed coverage
Adoption:             [M]  N of M eligible services
Deviations recorded:  [M]  count + top reasons
Owner:                [M]
```

**Trigger to build one [M]:** the same finding class appears in **three** systems. At that point
stop fixing instances — the cause is a missing platform capability, and metric M-9 will keep
rising until it exists.

---

## Defensibility gate record

```markdown
# Gate Record — <service> — <release>

Log sources present and ARRIVING:   [ ] verified by query at ____ UTC
Detections for top threat-model path:[ ] DET-____
Alert routes to a real queue:        [ ] queue ____ owner ____
Runbook exists:                      [ ] link ____
Backup configured AND restore tested:[ ] drill ref ____
Rollback documented and TIMED:       [ ] ____ minutes, verified ____
Workload identity least-privileged:  [ ] roles enumerated ____
Credential lifetime bounded:         [ ] ____

OUTCOME: [ ] PASS  [ ] PASS WITH CONDITIONS (dated: ____)  [ ] BLOCK
Reviewer: ____  Date: ____
If waived: risk accepted by System Owner ____ on ____, expiry ____
```

---

## SOAR playbook

```markdown
# Playbook — <name>

Trigger:              [M]  detection ID(s)
Enrichment steps:     [M]  automated, non-destructive -- automate these freely
Decision point:       [M]  what a human must decide
**Destructive actions:[M]  isolate / disable / revoke / kill
                            -> REQUIRE HUMAN APPROVAL. No exceptions.
                            -> System Owner pre-approval recorded: ____
                            -> Rollback: ____ (and how long it takes)**
Failure behavior:     [M]  what happens if a step fails -> default is STOP and page
Tested:               [M]  date + result
Review due:           [M]  annual
```

---

## Restore drill record

```markdown
# Restore Drill — <system> — <date>

System / data class:      [M]
Target RTO / RPO:         [M]
Restore destination:      [M]  **isolated environment -- never over the live system**
Owner notified:           [M]  (this is not a surprise test)

MEASURED:
  Time to first byte:     [M]
  Time to usable:         [M]  <- the real RTO
  Actual data loss window:[M]  <- the real RPO
  Data verified usable:   [M]  how? (opened / queried / app started)
                                "the job completed" is NOT verification

Gap vs target:            [M]
Issues encountered:       [M]
Remediation items:        [M]  work item IDs
Evidence for:             CP-4, CP-9/10 (800-53) · CC7.5 (SOC 2) · A.5.29/A.8.13 (ISO)
```
