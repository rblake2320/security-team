# §13 — Pilot Exercise: **Identity → Cloud**

← [Index](../README.md) · Prev → [§12 Roadmap](11_implementation_roadmap.md) · Next → [§14 Final Recommendation](13_final_recommendation.md)

**Selected focus:** IDENTITY → CLOUD (per Open Decision **O-13** default).
**Why this one:** identity is the most common initial access and privilege path in cloud and
hybrid environments; it is testable without touching application data; the telemetry is
centralized and well-understood; and every organization has it. Alternates are scoped at §13.15.

**Exercise ID:** `EX-2026-001` (pilot) · **Classification:** INTERNAL ·
**Environment:** lab tenant + pre-production, with **observation-only** production detection
validation in the final test case.

---

## 13.1 Business justification

| | |
|---|---|
| **Risk register reference** | R-004 *"Compromise of a workforce or workload identity leads to unauthorized access to cloud-hosted business data"* (default per O-11 ranking #1) |
| **Business impact if realized** | Unauthorized access to production data stores; regulatory notification exposure; loss of customer trust; potential ransomware staging path |
| **Why now** | Identity is the control plane for a hybrid/cloud estate. If identity telemetry is incomplete or identity attacks are undetected, **every downstream detection investment is built on sand.** |
| **Decision this exercise informs** | Whether to fund (a) identity detection engineering, (b) identity telemetry expansion, or (c) preventive identity controls — and in what order. These are three different budget lines and the exercise tells you which one you actually need. |
| **Cost** | ~20 person-days across all teams; no new tooling required |

---

## 13.2 Hypothesis (falsifiable)

> **H1:** A credential-guessing campaign against cloud identities (low-and-slow, from a single
> source, across many accounts) will be **detected within 30 minutes** and **contained within
> 2 hours**.
>
> **H2:** Successful authentication with a valid credential from an anomalous location, followed
> by enumeration of cloud resources, will generate an alert that a SOC analyst **correctly
> triages as suspicious** within 1 hour.
>
> **H3:** Creation of a new credential on an existing service principal / workload identity —
> a common persistence pattern — will be **logged and alerted**.

**Explicitly not the objective:** obtaining administrative access, accessing real data, or
demonstrating that compromise is possible. **"Red won" is not a result this exercise can
produce.**

---

## 13.3 Simulated adversary behavior

Modeled on widely reported, commodity-level cloud identity intrusion patterns — deliberately
**not** a specific named actor, and deliberately at the low-sophistication end. The pilot's
purpose is to establish the process, not to stress the defenders.

```
1. RECON        Identify the tenant's authentication endpoints from public information
                     (no interaction with production identities)
2. ACCESS       Low-and-slow credential guessing against SYNTHETIC lab accounts
                     (few attempts per account, spread over time, from one registered source)
3. FOOTHOLD     Authenticate as a synthetic account holding a valid, pre-seeded credential
4. DISCOVERY    Enumerate directory objects, groups, roles, and cloud resources
                     (read-only, lab tenant)
5. PERSISTENCE  Add a new credential to a synthetic workload identity (lab only)
6. EXFIL SIM    Read a marked canary object and move it to an org-controlled internal endpoint
                     (synthetic data, never leaves the org)
```

**Deliberately excluded from the pilot** (defer to later, more mature exercises):
token theft or replay against real identities · any technique intended to evade detection ·
lateral movement to on-premises systems · any destructive or availability-affecting action ·
any action against production identities.

---

## 13.4 ATT&CK mapping

| TC | Test case | Tactic | Technique | Environment |
|---|---|---|---|---|
| TC-001 | Passive discovery of authentication endpoints from public sources | Reconnaissance (TA0043) | T1590 *Gather Victim Network Information* | External / passive |
| TC-002 | Low-and-slow credential guessing across synthetic accounts | Credential Access (TA0006) | **T1110.003** *Password Spraying* | Lab tenant |
| TC-003 | Successful authentication from an anomalous source with a valid synthetic credential | Initial Access (TA0001) | **T1078.004** *Valid Accounts: Cloud Accounts* | Lab tenant |
| TC-004 | Directory and group enumeration | Discovery (TA0007) | **T1087.004** *Account Discovery: Cloud Account* | Lab tenant |
| TC-005 | Cloud resource and permission enumeration | Discovery (TA0007) | **T1580** *Cloud Infrastructure Discovery* | Lab tenant |
| TC-006 | Add credential to an existing synthetic workload identity | Persistence (TA0003) | **T1098.001** *Account Manipulation: Additional Cloud Credentials* | Lab tenant |
| TC-007 | Enumerate accessible cloud storage | Collection (TA0009) | **T1530** *Data from Cloud Storage* | Lab tenant |
| TC-008 | Move a marked canary object to an internal org-controlled endpoint | Exfiltration (TA0010) | **T1567** *Exfiltration Over Web Service* (simulated) | Lab tenant |
| TC-009 | **Production detection validation — observational only.** Confirm the detections proven in lab are deployed to production and that the required log sources are live and current. **No adversary action in production.** | — | — | **Production (read-only)** |

> **TC-009 is the most important test case in the pilot and the one most often skipped.** A
> detection that works in lab and is not deployed — or is deployed against a log source that
> stopped reporting three weeks ago — provides exactly zero production security. It also
> demonstrates that production validation is possible without production exploitation, which
> sets the pattern for every future exercise.

---

## 13.5 Test data — synthetic and lab-only **[M]**

| Data | Specification |
|---|---|
| Identities | 40 synthetic accounts, `svc-ex-2026-001-user-NN`, created for the exercise in the **lab tenant only**, no production federation, no mailbox, no licenses |
| Credentials | Generated for the exercise, unique, never reused, revoked at close. **No real user credential is used, guessed at, or handled at any point.** |
| Canary object | A generated file containing clearly marked synthetic content: `SYNTHETIC-EXERCISE-DATA-EX-2026-001-DO-NOT-USE`, plus a canary token to prove movement |
| Workload identity | One synthetic service principal / workload identity created for TC-006, no production role assignments |
| Storage | Lab storage container, empty except for the canary object |
| **Prohibited** | Any production identity · any real user data · any real credential material · any production federation or trust relationship |

**Synthetic-data rule [M]:** if a test case cannot be performed with synthetic data, it does not
run in the pilot. That constraint is what makes a first exercise safe enough to actually get
approved.

---

## 13.6 Expected telemetry

Purple predicts this **before** execution. Any gap between prediction and observation is itself
a finding.

| TC | Expected source | Expected signal | Latency target |
|---|---|---|---|
| TC-002 | Cloud IdP sign-in logs | Repeated failures, distinct accounts, single source IP, consistent user agent | <5 min ingestion |
| TC-003 | Cloud IdP sign-in logs | Successful auth; anomalous location/ASN; risk score if the platform produces one | <5 min |
| TC-004 | Directory audit logs | Directory read operations at atypical volume for the identity | <10 min |
| TC-005 | Cloud control-plane / activity logs | List/describe API calls across services from one identity | <10 min |
| TC-006 | Directory audit logs | Credential added to a service/workload identity — **a high-fidelity, low-volume event** | <10 min |
| TC-007 | Cloud storage access logs | List/read operations on the lab container | <15 min |
| TC-008 | Storage + network/proxy logs, canary callback | Object read; canary token triggered | <5 min (canary is immediate) |
| TC-009 | Telemetry health dashboard | All the above sources present, current, and within retention in **production** | Continuous |

**Prediction discipline [M]:** record predictions in the test case before execution. Comparing
prediction to reality separates "our detection failed" from "we were watching the wrong data" —
two problems with completely different owners and budgets.

---

## 13.7 Expected detections

| TC | Detection expectation | If absent |
|---|---|---|
| TC-002 | Threshold/cardinality detection: N failures across M distinct accounts from one source within a window | Detection Gap → Green (**highest-priority pilot outcome**) |
| TC-003 | Impossible-travel or anomalous-location sign-in, or IdP-native risk detection surfaced into the SIEM | Detection Gap → Green |
| TC-004 | Anomalous directory enumeration volume | Likely gap; commonly missing; low-noise variants exist |
| TC-005 | Cloud enumeration behavior detection | Likely gap; often high-noise — tune, do not force |
| TC-006 | **Credential added to a service principal / workload identity** | If this is not detected, it is the pilot's flagship finding. It is rare, high-fidelity, and a well-known persistence path. |
| TC-007 | Storage enumeration by an unusual identity | Depends on storage logging being enabled at all — often the real finding |
| TC-008 | Canary token fires; egress/proxy detection | Canary should always fire — if it does not, the canary infrastructure is broken and that is worth knowing |
| TC-009 | N/A — validating deployment and telemetry health, not behavior | Missing production deployment → Control Gap |

**Expected pilot outcome (a realistic prediction, not a target):** 2–4 detections fire, 3–5 gaps
found, 1–2 telemetry gaps found. **A pilot that detects everything means the scope was too easy;
a pilot that detects nothing means telemetry is the problem, not detection.** Both are useful and
both are reportable.

---

## 13.8 Safe execution procedure

### Pre-execution checklist **[M] — all must be ✓ before any activity**
```
[ ] RoE signed by all parties (RoE 5.18)
[ ] Safety assessment approved by White
[ ] System owner (lab tenant + production observer scope) signed
[ ] Legal + Privacy approved (synthetic data only -> expedited but NOT skipped)
[ ] Emergency contact roster live-tested within 5 business days
[ ] Exercise identities created, tagged EX-2026-001, expiry set
[ ] Source infrastructure registered and provided to SOC leadership
[ ] Deconfliction channel live; SOC lead briefed; 5-minute SLA confirmed
[ ] All test cases dry-run in lab
[ ] Rollback verified: identity deletion, credential revocation, canary removal
[ ] Production change freeze checked
[ ] White Exercise Director present or immediately reachable
[ ] Scribe assigned
```

### Execution sequence
| Day | Activity | Controls |
|---|---|---|
| **Day 1 AM** | Brief. Verify checklist. Confirm SOC is in normal operations (not handling a real incident). | White confirms go |
| **Day 1 PM** | TC-001, TC-002. Low-and-slow: **≤5 attempts per account per hour, ≤40 accounts, over ~3 hours**, from the single registered source. | Rate capped by procedure and by a lab tenant lockout policy set for the exercise |
| **Day 2 AM** | TC-003, TC-004, TC-005. Authenticate with the pre-seeded synthetic credential; read-only enumeration. | **Read-only. No modification of any object except TC-006's designated synthetic identity.** |
| **Day 2 PM** | TC-006, TC-007, TC-008. Credential addition to the synthetic workload identity; canary object read and movement to the internal endpoint. | Every created artifact recorded at creation for cleanup |
| **Day 3 AM** | TC-009. Production observational validation: query production telemetry health and confirm detection deployment. **No adversary action.** | Read-only production queries by Purple; no changes |
| **Day 3 PM** | Cleanup + verification by a non-operator. Collaborative validation session. | Cleanup checklist (RoE §5.14) |
| **Day 4** | Findings classification; evidence manifest; hot wash | |

### Ongoing controls during execution
- Deconfliction contact available continuously; every SOC query logged as an exercise event
- Daily update posted at 09:00 and 17:00 ([§6.3](05_communication_protocol.md))
- All activity from the single registered source IP with the exercise user-agent marker
- Any deviation from the test-case procedure requires written White approval **before** execution
- Rate limits are procedural **and** enforced by lab tenant configuration — belt and braces

---

## 13.9 Stop conditions (pilot-specific, in addition to RoE §5.13)

| Condition | Action |
|---|---|
| Any authentication attempt observed against a **production** identity | **Immediate stop.** Scope violation. White investigates before anything resumes. |
| Lab tenant lockout affecting anything outside the synthetic account set | Immediate stop; verify isolation |
| Canary token fires from an unexpected source | **Immediate stop — treat as a possible real incident** |
| SOC declares a real incident for any reason | Immediate stop; exercise yields to reality |
| Any production impact of any kind | Immediate stop |
| TC-009 production queries return unexpected sensitive content | Stop; do not read further; notify Privacy |
| Deconfliction contact unreachable for >15 minutes | Immediate stop |
| Any participant calls stop | Immediate stop, no justification required |

---

## 13.10 Engineering actions by team

### Yellow — before
- Confirm no production federation, trust, or role assignment touches the lab tenant **[M]**
- Provide the identity and cloud architecture for the threat model
- Name the engineer who will own remediation before the exercise starts (not after)

### Yellow — after
- Remediate application-layer findings (e.g. hardcoded workload credentials, over-permissive
  application registrations, missing token validation)
- Add regression tests: policy-as-code checks that fail the build on over-permissive identity
  configuration
- Update the threat model with what was learned

### Green — before
- Verify telemetry: which identity and cloud log sources exist, where they land, retention, latency
- Document current identity detections and their ATT&CK mapping
- Ensure the lab tenant logs to the same pipeline as production **[M]** — otherwise the lab
  result does not transfer and the whole exercise proves nothing about production

### Green — after
- Build/tune detections for every gap, prioritizing **TC-006** (highest fidelity, lowest noise)
- Onboard any missing log source; if not feasible, record a Control Gap with the reason and cost
- Add preventive controls where cheaper than detection: conditional access, blocking legacy
  authentication, workload-identity credential lifetime limits, sign-in risk policies
- Verify detections deploy to production, not only lab (this is the TC-009 remediation path)
- Add telemetry health monitoring for every source the pilot depended on

### Orange — before
- Facilitate the identity threat model with Yellow and Green
- Produce abuse cases: *"what can an attacker do with a workload identity that has these
  permissions?"*
- Perform attack-path analysis from identity to the crown-jewel data store — **this often finds
  more than the exercise itself**

### Orange — after
- Convert findings into safe regression tests (policy checks, not exploitation)
- Run a developer session: how identity design decisions created the paths found
- Add the discovered paths to the internal attack-path catalog

---

## 13.11 Purple validation steps

For each test case, in the collaborative session, record:

```
TC-006  Add credential to synthetic workload identity          T1098.001
--------------------------------------------------------------------------
1. PREVENTED     [ ] blocked  [x] not blocked
                 Evidence: EV-...-021 (operation succeeded, timestamp)
2. LOGGED        [x] full  [ ] partial  [ ] none
                 Source: directory audit log; event present at T+02:14
                 Fields present: actor, target, credential type, source IP
3. ALERTED       [ ] alerted  [ ] fired-suppressed  [x] no alert
                 -> DETECTION GAP GAP-2026-0003, priority P1
4. INVESTIGATED  [x] n/a -- no alert to triage
5. CONTAINED     [x] no
6. REPORTED      [x] no

TIME TO DETECT:  n/a
NOTES:           High-fidelity event, present in logs, no detection content exists.
                 Estimated FP volume: very low. Recommended: build first.
EVIDENCE:        EV-...-021, EV-...-022 (log export, hashed)
```

**Session rules [M]:** Red discloses exactly what was done and when. Blue discloses exactly what
was seen. Scoring is against the **pre-declared** criteria in §13.12 — not adjusted afterward to
make the result look better or worse. Findings are about systems, never about people.

---

## 13.12 White Team scoring criteria — **published before execution [M]**

### Process score (60% — the pilot is primarily a test of the *process*)
| Criterion | Points | Evidence |
|---|---|---|
| Complete authorization before any activity | 15 | Signed RoE, authorization records |
| All activity within approved scope | 10 | Event log vs. RoE §5.3 |
| Deconfliction worked (all queries answered <5 min) | 10 | Deconfliction log |
| Evidence complete, hashed, and retrievable | 10 | Evidence manifest |
| Stop conditions understood and executable (tested at least once, even artificially) | 5 | Stop test record |
| Cleanup complete and verified by a non-operator | 5 | Cleanup checklist |
| Daily updates and decision log maintained | 5 | Channel archive |

### Outcome score (40%)
| Criterion | Points | Notes |
|---|---|---|
| Test cases executed as planned | 10 | Deferrals with documented reason score full |
| Six-stage outcomes recorded with evidence for every case | 10 | Completeness, not favorability |
| Findings have testable acceptance criteria and named owners | 10 | |
| Predicted vs. observed telemetry documented | 10 | Gaps found score the **same** as gaps absent — this is deliberate |

### Scoring rules [M]
- **Detection rate does not affect the score.** The pilot measures whether the *process* works.
  Scoring the organization on detection performance in its first exercise teaches everyone to
  pick easy scenarios forever.
- A safety stop **does not reduce** the score. A safety stop that was **ignored** scores zero
  overall and triggers a program review.
- Any activity outside approved scope scores zero overall regardless of other results.

**Pass threshold: 80/100.** Below 80 → remediate the process and re-run a pilot before scaling
cadence. Do not proceed to Phase 4 on a failed pilot.

---

## 13.13 Required evidence

| Evidence | Captured by | Format | Marking | Retention |
|---|---|---|---|---|
| Signed RoE + authorization records | White | PDF, signed | INTERNAL | 7 yr |
| Safety assessment | White | Document | INTERNAL | 7 yr |
| Exercise event log (all test actions, UTC) | Purple + scribe | JSON ([§6.4.1](05_communication_protocol.md)) | INTERNAL | 7 yr |
| Log exports for each expected telemetry source | Purple + Green | JSON/CSV, hashed | INTERNAL | 7 yr |
| Alert records (fired and not-fired queries) | Green | Export | INTERNAL | 7 yr |
| Screenshots of key states | Operator | PNG, redacted at capture | INTERNAL | 7 yr |
| Six-stage outcome table | Purple | Structured | INTERNAL | 7 yr |
| Findings | Purple | JSON ([§6.4.2](05_communication_protocol.md)) | INTERNAL | 7 yr after closure |
| Deconfliction log | White | Channel export | INTERNAL | 7 yr |
| Decision log incl. all stops | White | Structured | INTERNAL | 7 yr |
| Cleanup verification | Non-operator | Checklist, signed | INTERNAL | 7 yr |
| Identity revocation confirmation | Identity owner | Export | INTERNAL | 7 yr |
| Evidence manifest with hashes | White custodian | Structured | INTERNAL | 7 yr |
| AAR | White | Document | INTERNAL | 7 yr |
| Destruction certificate (synthetic data) | White + Privacy | Signed | INTERNAL | 7 yr |

---

## 13.14 Retest process

| Step | Detail |
|---|---|
| **Trigger** | Remediation deployed and fix evidence submitted |
| **Timing** | Next bi-weekly retest batch after deployment; Critical findings retested within 5 business days |
| **Authorization** | Retests run under the **original RoE** if within its window; otherwise an abbreviated retest RoE referencing the original — **still signed** |
| **Procedure** | Re-execute the original test case **verbatim** in the same environment. Do not adapt it. If the original procedure is no longer possible because the system changed, record that as the outcome rather than substituting a different test. |
| **Recording** | Retest Record ([§6.4.4](05_communication_protocol.md)) with original outcome, retest outcome, delta, verdict |
| **Success** | Verdict `closed`; add to the automated regression suite; close the finding |
| **Partial** | Verdict `partially_remediated`; finding stays open with revised acceptance criteria and a new target date; do **not** close on partial |
| **Failure** | Verdict `not_remediated`; escalate to the System Owner; either re-remediate or sign a risk acceptance with expiry |
| **Regression watch** | Automated regression test runs on every deploy; a failure creates a new finding automatically, linked to the original |

**Retest of TC-006 (the flagship expectation):**
```
Original:  logged=full, alerted=no_alert, investigated=n/a
Remediation: Green ships detection DET-xxxx on the directory audit source;
             tested to fire in lab before production deployment
Retest:    Re-execute TC-006 verbatim in lab
Expected:  logged=full, alerted=alerted(DET-xxxx), investigated=correct
Then:      Repeat TC-009 -- confirm DET-xxxx is deployed to PRODUCTION and its
           source is live. Lab-only remediation does not close the finding.
Regression: Policy-as-code check fails any build adding a credential to a
           workload identity outside the approved provisioning path
```

---

## 13.15 Alternate pilot scopes (if O-13 resolves differently)

| Scope | Hypothesis | Core ATT&CK | Primary risk to manage | Relative difficulty |
|---|---|---|---|---|
| **API** | Broken object-level authorization in a business API is detected before data is enumerated | T1190, T1078 | Real data exposure — **use a seeded synthetic tenant** | Low–medium |
| **Supply chain** | An unauthorized dependency or build-step change is detected before it reaches production | T1195.002, T1554 | Do not test upstream projects; test **your** pipeline only | Medium |
| **AI system** | Indirect prompt injection via retrieved content causes an agent to exceed its tool permissions, and this is detected | No mature ATT&CK coverage — map to SA-11/SI-4 and document the gap | Model/tool sprawl; unclear ownership; frameworks lag the risk (conflict F-8) | **High — do not choose for a first pilot** |
| **Application** | A known weakness class is caught by CI before merge, and by detection if deployed | T1190, T1059 | Scope creep into a full appsec assessment | Low |
| **Cloud (posture)** | A drifted, over-permissive cloud configuration is detected and remediated within SLA | T1078.004, T1580 | Noisy findings overwhelming the pilot backlog | Medium |

**Recommendation: run Identity → Cloud first regardless of long-term priority.** It exercises
every stage of the workflow, it is safe with synthetic data, its telemetry is centralized, and
its findings are almost always actionable. Whatever your top risk is, you will test it better
after the process has been proven once on this.
