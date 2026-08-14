# GREEN TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

---

## 1. Workflow stages Green owns

| Stage | Green's role | Gate |
|---|---|---|
| 5 · Threat modeling | C — "what can we actually see?" | Instrumentation gaps recorded |
| 7 · Safety validation | R — technical review of blast radius | |
| 9 · Detection validation | R (Purple accountable) | Green never self-attests (SoD-1) |
| 11 · Remediation (detection/control items) | **R** | New content tested to fire **before** deployment |
| 17 · Backlog update | **A** (detection backlog) | Priority reflects fidelity, not novelty |
| — · Defensibility gate | **A** — blocking authority | Waivers require signed risk acceptance |

---

## 2. Weekly rhythm

| Day | Activity |
|---|---|
| Mon | Telemetry health review — **first thing, every week**. Any source below 99% is the week's top priority. |
| Tue | Detection engineering: build, test, tune |
| Wed | Bi-weekly detection backlog grooming with SOC + Purple |
| Thu | Paved-road / platform work; defensibility gate reviews for upcoming releases |
| Fri | FP review: any detection >50% FP for 30 days gets tuned, downgraded, or **retired** |
| Monthly | Restore drill for one critical system |
| Quarterly | Detection catalog audit: what has never fired? what has never had a true positive? |

**Telemetry health goes first, always.** Every detection is conditional on its data source. A
week spent writing rules against a source that stopped reporting is a week spent on nothing.

---

## 3. Runbook — detection engineering

```
1. INTAKE       Detection Gap (GAP-YYYY-NNNN) from Purple. Confirm:
                  - required data source EXISTS and is healthy
                  - if not: this is a TELEMETRY gap first. Raise a Control Gap for
                    the log source and mark the detection work BLOCKED. Do not
                    accept work that cannot succeed.
2. PRIORITIZE   Fidelity first, not novelty:
                  P1 = high fidelity, low volume, high impact
                       (e.g. credential added to a workload identity)
                  P4 = low fidelity, high volume, needs enrichment to be viable
                Build P1s first. They cost nothing to operate and buy credibility.
3. DESIGN       Behavior, not signature. Name the expected FP drivers BEFORE writing
                the logic -- if you cannot name them, you do not understand the data.
4. BUILD        Detection-as-code, in Git, with a unit test over sample events.
5. TEST         Fire it in a NON-PRODUCTION environment against the actual technique.
                A detection that has never been observed to fire is a hypothesis.
6. REVIEW       Peer review in Git. A second engineer, always (SoD-1).
7. DEPLOY       Through the normal change path. Record the deploy time --
                you will need it to answer "when did this detection start existing?"
8. VALIDATE     PURPLE re-executes the test case. Green does not self-attest.
9. TUNE         Watch FP rate for 30 days. Tune, downgrade, or RETIRE.
                Retirement is a legitimate and under-used outcome.
10. DOCUMENT    ATT&CK mapping, data source, expected volume, runbook link,
                and what to do when it fires.
```

---

## 4. Runbook — the defensibility gate

Applied before a service reaches production. **Green has blocking authority.**

```
REQUIRED LOG SOURCES
  [ ] Authentication / authorization decisions emitted and queryable
  [ ] Administrative and configuration changes logged
  [ ] Data access logged at the required granularity for its classification
  [ ] Errors and failures distinguishable from attacks
  [ ] Verified ARRIVING in the pipeline -- not merely "configured"

REQUIRED DETECTIONS
  [ ] At least one detection for the top attack path in the threat model
  [ ] Alert routes to a real queue with a real owner
  [ ] Runbook exists: what to do when it fires

REQUIRED RESILIENCE
  [ ] Backup configured AND a restore tested for this data class
  [ ] Rollback procedure documented and TIMED
  [ ] Dependency failure behavior known

REQUIRED IDENTITY
  [ ] Workload identity least-privileged; role assignments enumerated
  [ ] Credential lifetime bounded; rotation path exists
  [ ] No shared or static credentials

OUTCOME:  PASS  |  PASS WITH CONDITIONS (dated)  |  BLOCK
```

**Publish the waiver rate monthly.** A gate waived more than ~20% of the time is not a gate —
either resource it properly or lower it deliberately and say so. Quiet erosion is the worst
outcome because everyone still believes the gate exists.

---

## 5. Runbook — telemetry health

```
MONITOR   Per source: last event received, volume vs. 7-day baseline, latency, error rate
ALERT     Source silent > 2x its normal max gap  -> page. Treat as an outage.
          Volume down >50% vs. baseline          -> investigate same day
INVESTIGATE  Agent down? Pipeline broken? Permission changed? Cost control kicked in?
             Quota exceeded? A "cost optimization" that silently drops a source is
             the most common cause and the hardest to notice.
IMPACT    List every detection depending on the source. Those detections are DOWN.
          Tell the SOC explicitly -- silent detection failure is the worst failure mode
          in the entire model, because everyone continues to believe they are covered.
RECORD    Downtime feeds metric M-10, and caveats every coverage claim in that period.
```

---

## 6. Runbook — restore drills

```
Quarterly, one critical system per drill. Rotate through the estate.

1. Pick the system. Notify the owner. This is not a surprise test --
   surprise DR tests damage trust and produce worse data.
2. Restore to an ISOLATED environment. Never over the live system.
3. MEASURE: time to first byte, time to usable, data loss window (actual RPO).
4. VERIFY the restored data is actually usable -- open it, query it, run the app.
   "The restore job completed" is not verification.
5. Compare measured RTO/RPO against the stated target. Report the gap honestly.
6. Record. This is compliance evidence (CP-4, CP-9/10, CC7.5, A.5.29) AND the only
   real answer to "are we ransomware-resilient?"
```

**Backup success reports are not evidence of recovery capability.** The gap between "backups are
green" and "we restored it and it worked" is where ransomware incidents become extinction events.

---

## 7. Escalation

| Situation | Escalate to |
|---|---|
| Log source down and cannot be restored | Green Lead → Security Engineering Director; **notify SOC that detections are down** |
| Detection needs a destructive automated response | System Owner (approval) + documented rollback |
| Gate blocking a release under pressure | Engineering Director + System Owner; signed risk acceptance is the only override |
| Telemetry cost forcing source cuts | **CISO — this is a risk decision, not a budget decision.** Present it as "we will lose detection of techniques X, Y, Z." |
| Purple says a detection did not fire | Investigate first, argue never. Purple's empirical result wins. |

---

## 8. Metrics Green owns

**M-10 telemetry availability (the foundation — everything else is conditional on it)** ·
M-3 detection rate · M-11 false-positive rate · time from gap identified to content deployed
(target ≤15 business days) · defensibility gate pass rate · restore drill RTO/RPO vs. target ·
paved-road adoption.

---

## 9. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Reporting rule counts | Report validated coverage (M-1) and FP rate (M-11) |
| Deploying detections that have never been observed to fire | Test in non-prod against the actual technique first |
| Green attests its own detection works | Purple validates. Always. (SoD-1) |
| Ignoring FP rate because the detection is "important" | A detection analysts ignore does not exist. Tune, downgrade, or retire. |
| Detections authored only in the SIEM UI | Detection-as-code in Git |
| Backup reports treated as recovery evidence | Restore drills with measured RTO/RPO |
| Accepting a detection gap whose data source does not exist | Raise the telemetry gap first; blocked work is not work |
| Quietly cutting a log source for cost | Escalate as a risk decision with named lost coverage |
