# §8 — Metrics

← [Index](../README.md) · Prev → [§7 Artifacts](06_artifact_index_and_standards.md) · Next → [§9 Toolchain](08_toolchain_architecture.md)

**Design rule:** every metric here answers *"what would I do differently if this number moved?"*
If a metric cannot change a decision, it is not reported. A list of banned vanity metrics is at
§8.18 — read it before adding anything to a dashboard.

**Universal reporting rules [M]:**
- Report **trend + denominator**, never a bare number. "47 detections" is meaningless; "detected
  9 of 14 prioritized techniques, up from 6 of 14" is a decision input.
- Never report per-analyst or per-engineer performance from this data. The moment these numbers
  affect someone's review, they stop describing reality.
- Every metric names an owner and a data source that a second person could reproduce.
- Metrics derived from fewer than 5 observations are reported with the raw count, not a percentage.

---

## M-1 · ATT&CK coverage

| | |
|---|---|
| **Formula** | `Coverage% = (techniques with >=1 validated detection OR prevention) / (techniques on the PRIORITIZED list) x 100` |
| **Critical qualifier** | Denominator is the **prioritized** technique list — techniques relevant to your environment, threat model, and named actors. **Never use all ~600+ ATT&CK techniques**; that denominator makes every organization look failing and drives no decision. Prioritized list is typically 40–120 techniques. |
| **Denominator source of truth [M]** | **`blue-team/config/coverage_target.json`** — version-controlled, machine-readable, with priority and required telemetry per technique. Maintained jointly by Purple and Blue; edits are logged in Blue's changelog because they change every coverage number in the program. An unstated denominator is the most common way this metric gets fudged. |
| **Validated means** | Purple executed the technique and observed prevention or detection. Vendor claims and rule-name matching do not count. |
| **Two columns, always reported side by side** | **Declared** coverage (Blue: `python -m blue_team.cli coverage` — a rule exists and its telemetry is present) vs. **Validated** coverage (Purple: it was tested and it fired). The gap between them is the most useful number on the slide (conflict C-7). |
| **Data sources** | Emulation library (numerator), `blue-team/config/coverage_target.json` (denominator), detection catalog, Blue's declared-coverage report |
| **Owner** | Purple Lead |
| **Frequency** | Monthly; ATT&CK Navigator layer regenerated quarterly |
| **Target** | +5–10 percentage points per quarter until ≥80% of prioritized techniques, then hold and deepen |
| **Decision it changes** | Where to point next quarter's exercises, and whether a coverage gap is a *detection* problem (Green) or a *telemetry* problem (Green/Yellow — a different budget line and a different fix). |
| **Anti-gaming** | Report **validated** coverage separately from **claimed** coverage. The gap between them is itself the most interesting number on the slide. |

---

## M-2 · Prevention rate

| | |
|---|---|
| **Formula** | `Prevention% = test cases with outcome_prevented in {blocked} / total test cases executed x 100` |
| **Segment by** | Technique, tactic, environment, control type |
| **Data sources** | Test case outcomes (six-stage stage 1) |
| **Owner** | Purple Lead |
| **Frequency** | Per exercise; rolled up quarterly |
| **Target** | No universal target. Track the trend; prevention is *preferred over detection* wherever it does not break the business. |
| **Decision it changes** | A technique consistently detected but never prevented is a candidate for a preventive control (conditional access policy, application control, egress restriction). Prevention is cheaper to operate than detection — it does not consume analyst time. |
| **Caution** | Prevention can be gamed by testing only what you already block. Denominator must come from the threat-informed list, not from what is convenient. |

---

## M-3 · Detection rate

| | |
|---|---|
| **Formula** | `Detection% = test cases with outcome_alerted = alerted / (test cases executed - test cases prevented) x 100` |
| **Why exclude prevented** | A blocked technique cannot be detected in the same sense. Including them inflates the number and hides real detection gaps. |
| **Companion metric** | `Triage% = investigated correctly / alerted x 100` — an alert nobody triages is not a detection |
| **Data sources** | Six-stage outcomes (stages 3 and 4), SIEM alert records |
| **Owner** | Purple Lead (measure), Green Lead (improve) |
| **Frequency** | Per exercise; quarterly trend |
| **Target** | ≥70% on prioritized techniques by month 12; ≥90% on Critical-risk techniques |
| **Decision it changes** | Detection rate low + telemetry present → Green detection engineering investment. Detection rate low + telemetry absent → log source / pipeline investment (bigger, slower, more expensive — and worth knowing before you fund the wrong one). |

---

## M-4 · Mean time to detect (MTTD)

| | |
|---|---|
| **Formula** | `MTTD = median(alert_timestamp - test_action_timestamp)` for detected cases |
| **Use median, not mean** | One 14-day outlier destroys a mean and hides the typical case. Report median **and** p90. |
| **Data sources** | Exercise event log (action time), SIEM (alert time) |
| **Owner** | Purple Lead |
| **Frequency** | Per exercise; quarterly trend by technique class |
| **Target (illustrative — set per O-7)** | Critical techniques ≤15 min; High ≤1 h; others ≤24 h |
| **Decision it changes** | MTTD dominated by *ingestion lag* → data pipeline work. Dominated by *rule schedule* → move to streaming/near-real-time rules. Dominated by *analyst queue depth* → staffing or alert-volume reduction. **These three have completely different fixes and the same symptom** — which is why MTTD must be decomposed, not just reported. |
| **Decomposition [R]** | `MTTD = ingestion_lag + rule_latency + queue_wait + triage_time`. Report the components. |

---

## M-5 · Mean time to investigate (MTTI)

| | |
|---|---|
| **Formula** | `MTTI = median(investigation_conclusion_time - alert_timestamp)` |
| **Conclusion** = the analyst reaches a correct disposition (escalate / benign / exercise) |
| **Data sources** | SOC case management timestamps |
| **Owner** | SOC Manager; reported by Purple |
| **Frequency** | Monthly |
| **Target** | Critical ≤30 min; High ≤4 h |
| **Decision it changes** | High MTTI with correct outcomes → enrichment/context problem (fix with SOAR enrichment, better runbooks, better alert context). High MTTI with wrong outcomes → training or detection-quality problem. Enriching an alert nobody understands does not help; the two causes need opposite investments. |

---

## M-6 · Mean time to contain (MTTC)

| | |
|---|---|
| **Formula** | `MTTC = median(containment_action_time - test_action_timestamp)` |
| **Note** | Measured from the *adversary action*, not from the alert. Containing 20 minutes after an alert that fired 6 hours late is not a 20-minute response. |
| **Data sources** | Exercise event log, EDR/identity action logs, IR case records |
| **Owner** | CSIRT commander; reported by Purple |
| **Frequency** | Per exercise; quarterly |
| **Target** | Critical ≤1 h; High ≤4 h (set against your own O-7 baseline, not an industry figure) |
| **Decision it changes** | MTTC gated by *authority* ("who can approve isolating a production host at 2am?") → pre-authorize containment actions in the IR plan. Gated by *tooling* → invest in SOAR/response automation. Gated by *knowledge* → runbooks. Authority is the most common cause and the cheapest to fix. |

---

## M-7 · Mean time to remediate (MTTR)

| | |
|---|---|
| **Formula** | `MTTR_severity = median(remediation_deployed_date - finding_created_date)` per severity |
| **Also report** | `% within SLA = findings closed within SLA / findings closed x 100` |
| **Data sources** | Case management + engineering backlog + deployment records |
| **Owner** | System Owner (accountable), Yellow (reports) |
| **Frequency** | Monthly |
| **Target** | ≥90% within SLA (Critical 7d / High 30d / Med 90d / Low 180d — adjust per O-3) |
| **Decision it changes** | Chronic SLA misses on one team → capacity or competing-priority problem, escalate to the System Owner and the portfolio, not to the engineers. Chronic misses across all teams → the SLA is unrealistic and should be renegotiated openly rather than ignored quietly. |
| **Integrity check [M]** | Audit severity changes quarterly. If MTTR improves while the count of severity downgrades rises, the metric is being managed rather than the risk. |

---

## M-8 · Retest success rate

| | |
|---|---|
| **Formula** | `Retest success% = retests with verdict=closed / total retests x 100` |
| **Data sources** | Retest Records |
| **Owner** | Purple Lead |
| **Frequency** | Monthly |
| **Target** | ≥85%. Below 70% is a systemic acceptance-criteria problem. |
| **Decision it changes** | Low retest success means fixes are being declared complete without meeting acceptance criteria. The fix is upstream — tighten acceptance criteria at stage 10 and enforce gate G5 — **not** more retesting. More retesting of bad fixes just costs more. |

---

## M-9 · Recurrence rate

| | |
|---|---|
| **Formula** | `Recurrence% = findings closed that later reappear (same technique + same asset class) within 12 months / findings closed x 100` |
| **Data sources** | Findings history, regression test results |
| **Owner** | Purple Lead |
| **Frequency** | Quarterly |
| **Target** | <5% |
| **Decision it changes** | **The single strongest signal that point fixes are being applied where a platform fix is needed.** High recurrence → stop fixing instances; fund a paved road (Green) or an architectural change (Yellow). Also drives regression-test investment (M-13). |
| **Why it matters most** | Recurrence is the metric that distinguishes a security program that is improving from one that is running in place while looking busy. |

---

## M-10 · Telemetry availability

| | |
|---|---|
| **Formula** | `Availability% = minutes each critical log source delivered data within expected latency / total minutes x 100`, per source |
| **Companion** | `Coverage% = assets reporting a required source / assets required to report it x 100` |
| **Data sources** | SIEM ingestion health, pipeline monitoring, CMDB |
| **Owner** | Green Lead |
| **Frequency** | Continuous monitoring; reported weekly |
| **Target** | ≥99% per critical source; ≥98% asset coverage |
| **Decision it changes** | **This is the foundation metric — every detection metric is conditional on it.** A silent log source means every detection depending on it is silently dead. Below target → pipeline engineering, agent deployment, or license/retention budget. |
| **Rule [M]** | Report M-1 and M-3 with a telemetry-availability caveat whenever any critical source was below 95% during the measurement period. Coverage claims computed over dead data sources are the most common way security dashboards lie. |

---

## M-11 · False-positive rate

| | |
|---|---|
| **Formula** | `FP% = alerts dispositioned false_positive / total alerts x 100`, per detection and overall |
| **Better companion** | `Alerts per analyst per shift` and `% of detections with zero true positives in 90 days` |
| **Data sources** | SOC case dispositions, SIEM |
| **Owner** | Green Lead (content), SOC Manager (disposition quality) |
| **Frequency** | Weekly per detection; monthly overall |
| **Target** | Detection-level FP% <20% for high-severity detections; zero detections exceeding 50% FP in production for more than 30 days |
| **Decision it changes** | A noisy detection is worse than no detection, because it trains analysts to dismiss a class of alert. Above threshold → tune, add enrichment, downgrade severity, or **retire the detection**. Retirement is a legitimate and under-used outcome. |
| **Caution** | Do not optimize FP% to zero — that produces detections so narrow they miss real variants. Optimize *analyst time per true positive*. |

---

## M-12 · Findings by severity and age

| | |
|---|---|
| **Formula** | Open findings bucketed: `severity x age {0-30, 31-60, 61-90, 90+ days}`; plus `median age of open findings by severity`; plus `intake:closure ratio` |
| **Data sources** | Case management |
| **Owner** | Purple Lead |
| **Frequency** | Monthly to leads; quarterly to exec |
| **Target** | Zero Critical >7 days without a signed risk acceptance; Highs aging past 60 days trending down; **intake:closure ratio ≤ 1.0 sustained** |
| **Decision it changes** | Aging Highs = a prioritization failure, escalate to System Owners. **Intake:closure > 1.0 sustained means the program is generating findings faster than the organization can absorb them — the correct response is to slow exercise cadence and fund remediation capacity.** Running more exercises at that point actively harms the program's credibility. |

---

## M-13 · % of findings converted into automated regression tests

| | |
|---|---|
| **Formula** | `Regression% = closed findings with a linked automated regression test / closed findings eligible for automation x 100` |
| **Eligibility** | Exclude findings where automation is genuinely infeasible (physical, process, one-off architecture) — and **record the exclusion reason** so "infeasible" cannot become a dumping ground |
| **Data sources** | Retest records, CI test suite, emulation library |
| **Owner** | Purple Lead + Yellow eng managers |
| **Frequency** | Monthly |
| **Target** | ≥60% by month 12; ≥80% by month 24 |
| **Decision it changes** | **This is the compounding metric.** Every automated regression test converts a one-time exercise finding into a permanent guard, which is what stops M-9 (recurrence) from rising as the system grows. Low values → invest in test tooling and in making the emulation library CI-runnable. |

---

## M-14 · % of systems with approved threat models

| | |
|---|---|
| **Formula** | `TM% = systems above the criticality threshold with an approved threat model reviewed within 12 months / systems above the threshold x 100` |
| **Currency requirement [M]** | A threat model older than 12 months, or predating a material architecture change, counts as **absent**. A stale threat model is worse than none because it creates false confidence. |
| **Data sources** | Architecture repo, CMDB/asset inventory |
| **Owner** | Orange Lead |
| **Frequency** | Quarterly |
| **Target** | ≥90% of above-threshold systems |
| **Decision it changes** | Low coverage → Orange capacity or process-gate problem (are threat models required at a specific SDLC gate, or merely encouraged?). Also predicts M-9: systems without threat models generate repeat findings. |

---

## M-15 · % of exercises stopped for safety reasons

| | |
|---|---|
| **Formula** | `Stop% = exercises with >=1 safety stop / exercises executed x 100`; also `stops per exercise` and `median stop duration` |
| **Data sources** | Stop events, Decision Log |
| **Owner** | White Exercise Director |
| **Frequency** | Quarterly |
| **Healthy band** | **5–20%.** This metric is a U-curve, not a "lower is better" metric. |
| **Decision it changes** | **0% over a year → stop conditions are not being enforced or people are afraid to call stop.** Investigate the culture; this is a serious finding, not a clean record. **>30% → planning quality problem**: safety assessments are missing risks that surface during execution; invest in stage 7. |
| **Report alongside** | Stops that were later found unnecessary — a healthy number is *non-zero*, and it should be celebrated publicly, or people will stop calling. |

---

## M-16 · Compliance-control coverage

| | |
|---|---|
| **Formula** | `Coverage% = controls with current evidence produced by this operating model / controls in the applicable baseline that this model can evidence x 100` |
| **Critical qualifier** | Denominator is **only** the controls this model can legitimately evidence (assessment, testing, monitoring, IR testing, secure development) — typically 15–25% of a baseline. **Never present this as overall compliance.** |
| **Data sources** | Evidence manifests, GRC control mapping (see [crosswalk](10_compliance_crosswalk.md)) |
| **Owner** | GRC |
| **Frequency** | Quarterly, and before any assessment |
| **Target** | 100% of the mappable subset, with evidence current per the framework's freshness expectation |
| **Decision it changes** | Gaps show which controls will need *manually produced* evidence at assessment time — the expensive kind. Closing them shifts audit cost from a scramble to a byproduct of normal operations. |
| **Prohibited claim [M]** | This metric never implies authorization, certification, or compliance. See [§11](10_compliance_crosswalk.md). |

---

## 8.17 Reporting pack structure

| Audience | Cadence | Contents | Length |
|---|---|---|---|
| **Team leads** | Monthly | All metrics, decomposed, with raw counts and open questions | Dashboard + 30 min |
| **CISO** | Monthly | M-1, M-3, M-4, M-7, M-9, M-12 with trends and the two decisions needed this month | 1 page |
| **Executive / Risk Committee** | Quarterly | Trend on M-3, M-6, M-9, M-12, M-16 + risk acceptances outstanding + top 3 decisions requiring their authority | 1 page + 30 min |
| **Board / Audit Committee** | Annually or on request | Program existence, independence attestation, top risks, trend direction, resourcing asks | 3 slides |
| **System Owners** | Monthly, per system | Their findings, ages, SLA status, active risk acceptances and expiry dates | Automated email |

**[M] Every metric slide carries its denominator and its data-quality caveats on the same slide.**
Footnoted caveats are not read; caveats on the same line as the number are.

---

## 8.18 Banned vanity metrics

Do not report these. Each is listed with what to report instead.

| Banned | Why it is a vanity metric | Report instead |
|---|---|---|
| Number of detections written | Rewards volume; 400 untested rules is worse than 40 validated ones | M-1 validated coverage, M-11 FP rate |
| Number of exercises run | Activity, not outcome | M-1 coverage delta, M-13 regression conversion |
| Number of vulnerabilities found | Rewards finding, punishes fixing; also rewards scanning noisier | M-12 age + intake:closure ratio |
| Total alerts processed | Measures noise volume | M-5 MTTI, alerts per analyst per shift |
| % of ALL ATT&CK techniques covered | Meaningless denominator; nobody covers 600+ techniques and nobody should try | M-1 against the prioritized list |
| Training completion % | Measures clicking, not capability | Exercise-derived capability outcomes (M-5 triage correctness) |
| Phishing click rate alone | Highly manipulable by campaign difficulty; drives blame | Report rate **with** difficulty tier + **report rate** (people who reported it) |
| Number of tools deployed | Confuses spend with capability | M-10 telemetry availability, M-3 detection rate |
| "Days since last incident" | Rewards not detecting incidents | M-4 MTTD, M-6 MTTC |
| Red Team "success" rate | Adversarial framing; encourages Red to optimize for wins over learning | Techniques validated, M-1, M-3 |
| Individual analyst detection stats | Destroys the data quality it measures; punishes honest disposition | Team-level M-5 with no individual attribution |
| Compliance % (overall) from this program | Overstates what testing evidence proves | M-16 with its explicit qualifier |
