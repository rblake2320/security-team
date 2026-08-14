# §5 — Rules of Engagement (Reusable Template)

← [Index](../README.md) · Prev → [§4 Workflow](03_end_to_end_workflow.md) · Next → [§6 Communication Protocol](05_communication_protocol.md)

---

**How to use this file:** copy it to the exercise record as `ROE-<ID>.md`, fill every field, and
route for signature. **Fields marked [M] may not be left blank, marked "TBD", or marked "N/A"
without a written justification in the field itself.** An RoE with an unfilled [M] field is not
approved, regardless of how many signatures it carries.

**Owner:** White Exercise Director · **Approver:** see §5.18 · **Retention:** 7 years (or the
longest applicable framework schedule) · **Marking:** set in §5.0 · **System of record:**
exercise record system / GRC platform

---

## 5.0 Document control

| Field | Value |
|---|---|
| Exercise ID **[M]** | `EX-YYYY-NNN` |
| Exercise name **[M]** | |
| RoE version **[M]** | v1.0 (increment on any change; changes after approval require re-signature by White + affected System Owners) |
| Classification / marking **[M]** | ☐ PUBLIC ☐ INTERNAL ☐ CONFIDENTIAL ☐ CUI (+ category & dissemination) ☐ Other: ____ |
| Distribution list **[M]** | Named individuals only. No group aliases. |
| Effective from / to **[M]** | UTC start — UTC end |
| Supersedes | |
| Related risk register IDs **[M]** | |

---

## 5.1 Written authorization **[M]**

> No activity described in this document is authorized until every signature in §5.18 is
> present and every condition is cleared. Verbal, chat-based, and email approvals do not
> constitute authorization under this document.

| Field | Value |
|---|---|
| Authorizing executive (sponsor) **[M]** | Name, title |
| Legal entity/entities covered **[M]** | |
| Authority basis **[M]** | ☐ Internal policy ref ____ ☐ Contract/PWS clause ____ ☐ Customer written consent ____ ☐ Regulatory requirement ____ |
| Third-party systems involved? **[M]** | ☐ No ☐ Yes → §5.15 mandatory |
| Testing performed by **[M]** | ☐ Employees ☐ Contractors (company, contract #) ☐ Both |
| Named individuals authorized to execute **[M]** | Full list. Anyone not named is not authorized. |
| Background/clearance verification complete **[M]** | ☐ Yes, date ____ |
| Insurance/regulatory notification required? **[M]** | ☐ No ☐ Yes → notified on ____ by ____ (see O-14) |

---

## 5.2 Objectives and hypothesis **[M]**

| Field | Value |
|---|---|
| Business objective **[M]** | What decision will this exercise inform? |
| Hypothesis **[M]** | Stated so it can be falsified. e.g. *"We will detect T1110.003 password spraying against Entra ID within 15 minutes and contain within 60."* |
| Success is NOT **[M]** | Explicitly state what does not count as success — e.g. "domain admin obtained" is not an objective. |
| Learning objectives | |
| Pre-declared scoring criteria **[M]** | Reference the Scoring Rubric. Must be fixed before execution. |

---

## 5.3 In-scope assets **[M]**

| Asset / system | Owner (named) | Environment | Data classification | Criticality | Permitted impact ceiling | Authorization ref |
|---|---|---|---|---|---|---|
| | | ☐ Lab ☐ Dev ☐ Pre-prod ☐ Prod | | | ☐ None ☐ Read-only ☐ Config change ☐ Service degradation | |

**Identification method [M]** — how an operator confirms a target is in scope *before* touching
it (exact hostnames, IP ranges/CIDRs, cloud subscription/account IDs, resource tags, repo URLs,
API endpoints, tenant IDs):

```
[list here — no wildcards without an explicit exception approved by White]
```

---

## 5.4 Excluded assets **[M]**

| Excluded asset / class | Reason | Absolute or conditional |
|---|---|---|

**Standing exclusions (apply to every exercise unless explicitly overridden in writing) [M]:**
- Safety-of-life, medical, and operational-technology/ICS systems
- Financial transaction systems during close periods
- Third-party/SaaS systems without documented provider authorization
- Systems under active incident response
- Systems in a declared change freeze
- Personal devices, personal accounts, and personal data of employees not acting in scope
- Anything not listed in §5.3 — **scope is allow-list, never deny-list**

---

## 5.5 Permitted actions **[M]**

| Action class | Permitted | Environment restriction | Conditions |
|---|---|---|---|
| Passive reconnaissance / OSINT | ☐ | | |
| Authenticated enumeration with issued exercise identity | ☐ | | |
| Vulnerability validation (non-exploitative confirmation) | ☐ | | |
| Controlled exploitation of a confirmed vulnerability | ☐ | ☐ Lab ☐ Pre-prod ☐ Prod | Requires named White approval per instance if Prod |
| Lateral movement | ☐ | | Depth limit: ____ hops |
| Privilege escalation | ☐ | | Ceiling: ____ (stop at this privilege level) |
| Data access (synthetic/marked data only) | ☐ | | Volume cap: ____ records |
| Data exfiltration **simulation** (marked canary data to an approved internal endpoint) | ☐ | | Destination must be org-controlled |
| Phishing / social engineering of employees | ☐ | | HR + Legal + Privacy concurrence [M] |
| Physical access testing | ☐ | | Separate authorization + carry letter [M] |
| Denial-of-service / load testing | ☐ | | Default **PROHIBITED**; lab-only if ever |
| Persistence mechanisms | ☐ | | Default **PROHIBITED**; if lab-only, must be documented, enumerated, and removed with verification |
| Credential material handling | ☐ | | See §5.9 |

## 5.6 Prohibited actions — absolute, no exception path **[M]**

The following are prohibited in **all** environments and **cannot** be authorized by this
document, by White, or by any system owner. Authorizing them requires a separate, differently
governed process.

1. Destructive actions: deleting, encrypting, corrupting, or ransoming data or systems
2. Modifying, disabling, or deleting security controls, logs, or audit trails to evade detection
3. Covert persistence intended to survive the exercise or evade cleanup
4. Accessing, viewing, copying, or transmitting real PII, PHI, CUI, cardholder data, classified
   material, or privileged communications — beyond the minimum needed to prove access exists,
   and never exfiltrated
5. Testing systems, accounts, or networks not listed in §5.3
6. Using real user credentials obtained during the exercise to access real user data
7. Techniques that could affect safety of life, medical care, or emergency services
8. Actions against third-party infrastructure without that party's written authorization
9. Deploying tooling that cannot be fully enumerated and removed
10. Continuing after a STOP has been called
11. Any action taken to make the exercise result look better or worse than reality

**Violation of §5.6 is a personnel and potentially legal matter, not a process deviation.**
It is reported by White to the Executive Sponsor and General Counsel within 24 hours.

---

## 5.7 Approved identities, infrastructure, and tools **[M]**

### Identities
| Exercise identity | Purpose | Privilege | Issued by | Issued at (UTC) | Expiry | Tag/marker | Revoked at |
|---|---|---|---|---|---|---|---|

**Rules [M]:**
- Exercise identities are purpose-created, uniquely named with a standard prefix
  (e.g. `svc-ex-<ID>-<n>`), attributable to the exercise, and time-bound to the window.
- Operators' normal accounts are never used for test activity.
- Identities are issued by an identity owner **outside** the exercise team (SoD-9).
- Revocation is verified by White at close, not asserted by the operator.

### Infrastructure
| Source IP / range | Hostname | Owner | Location | Purpose | Registered in deconfliction? |
|---|---|---|---|---|---|

All test-originating infrastructure must be **pre-registered and allow-listed in the
deconfliction record [M]** so SOC can attribute traffic in seconds.

### Tools
| Tool | Version | Purpose | Approved by | License/authorization | Environment limit |
|---|---|---|---|---|---|

**Rules [M]:** no unapproved tools; no tools obtained from untrusted sources; no tools that
cannot be enumerated and removed; commercial C2 or emulation frameworks require named White
approval, a defined configuration, and lab-first validation. Custom scripts are attached to the
exercise record.

---

## 5.8 Production versus lab restrictions **[M]**

| Environment | Permitted activity | Approval required | Additional controls |
|---|---|---|---|
| **Lab / range** | Full test-case set including exploitation | Purple Lead | Isolated; no production data; no production identity federation |
| **Dev** | Non-destructive validation | Purple Lead + System Owner | Synthetic data only |
| **Pre-production** | Exploitation permitted where the environment mirrors prod | White + System Owner | Must be data-sanitized; confirm no production integrations |
| **Production** | **Default: observation and detection validation only.** Exploitation requires explicit per-action White approval, System Owner presence, and a timed rollback plan. | White + System Owner + Executive Sponsor | Change freeze checked · backups verified within 24 h · on-call engaged · rollback rehearsed and timed · business-hours-only unless justified |

**Default posture [M]:** every test case runs in lab first. A test case that has not been
executed successfully in lab does not run in production. See Open Decision O-5.

---

## 5.9 Data collection, minimization, retention, destruction **[M]**

| Field | Value |
|---|---|
| Data classes that may be collected **[M]** | ☐ System metadata ☐ Log excerpts ☐ Screenshots ☐ Config exports ☐ Synthetic records ☐ Other: ____ |
| Data classes that may **never** be collected **[M]** | Real PII/PHI/CUI/CHD/classified content; full credential material; privileged communications; personal files |
| Minimization rule **[M]** | Collect the minimum needed to prove the finding. Proof of access ≠ extraction of data. One redacted screenshot beats a database dump, always. |
| Redaction requirement **[M]** | Redact at capture time, not at report time |
| Storage location **[M]** | Named, access-controlled, encrypted at rest, in an approved region/boundary |
| Encryption in transit/at rest **[M]** | |
| Access list **[M]** | Named individuals |
| Retention period **[M]** | Evidence: ____ (default 7 years or the longest applicable framework) · Raw captures: ____ (default 90 days) |
| Destruction method + date **[M]** | Method: ____ · Scheduled: ____ · Certificate required: ☐ Yes |
| Privacy approval **[M]** | Name, date |

### Handling of specific material types **[M]**
| Material | Rule |
|---|---|
| **Credentials/secrets discovered** | Do not use beyond proving validity once against a non-production target where possible. Report to the identity owner within **1 hour**. Rotate before the exercise ends. Never store in the exercise record — store only the fact of discovery, the location, and the rotation confirmation. |
| **PII / PHI** | Do not view, copy, or export. Record only: data class, record count estimate, and access path. Privacy Officer notified within 4 hours. |
| **CUI** | Handle per the applicable CUI category's marking, storage, and dissemination rules. Never leaves the authorized boundary. Never enters a chat tool, a general-purpose AI system, or a personal device. |
| **Cardholder data** | Do not access. If encountered, stop that test case and notify White + the CDE owner immediately. |
| **Classified information** | If encountered on a system not expected to hold it: **stop all activity immediately**, do not investigate further, secure the workstation, and notify the security officer per spillage procedure. This is a stop condition, not a finding. |
| **Privileged / attorney-client material** | Stop; notify Legal; do not read further. |

---

## 5.10 Test schedule **[M]**

| Field | Value |
|---|---|
| Window start / end (UTC + local) **[M]** | |
| Permitted hours **[M]** | e.g. Mon–Thu 09:00–17:00 local. Off-hours requires named White approval and on-call engagement. |
| Blackout periods **[M]** | Change freezes, financial close, peak business events, audits, holidays, other exercises |
| Deconfliction with other exercises **[M]** | Checked against exercise calendar on ____ by ____ |
| Notification schedule **[M]** | Who is told what, when — see [§6](05_communication_protocol.md) |
| Blind phase designated? | ☐ No ☐ Yes → **complete §5.10.1 in full** |

### 5.10.1 Blind phase — required schema **[M] if a blind phase is designated**

Purple is **collaborative by default**. A blind phase is a White-authorized *test mode*, not a
default posture, and it must be fully specified before execution.

```yaml
blind_phase:
  authorized: true
  authority_signature: "<signature>"          # White Exercise Director. Unsigned = not authorized.
  objective: "Measure unassisted baseline detection and response"
  participants_blinded:
    - blue_team
  information_withheld:
    - technique_sequence
    - execution_time
  start: "2026-08-14T14:00:00Z"
  end:   "2026-08-14T16:00:00Z"
  declassification_trigger: "End time or White Team termination"
  safety_observers:
    - white_controller_01
  real_incident_deconfliction: "procedure://IR-DECON-001"
```

| Field | Requirement |
|---|---|
| `authorized` + `authority_signature` | **[M]** An unsigned blind phase does not exist. Running one informally is a charter violation, not a test-design choice |
| `objective` | **[M]** Stated as something measurable. "To make it realistic" is not an objective |
| `participants_blinded` | **[M]** Named explicitly. Everyone not listed is *not* blinded |
| `information_withheld` | **[M]** Enumerated. Anything not listed is disclosed normally |
| `start` / `end` | **[M]** Bounded. See the expiry rule below |
| `declassification_trigger` | **[M]** End time **or** White termination — whichever comes first |
| `safety_observers` | **[M]** Named. Safety is never blinded — an observer always has full visibility |
| `real_incident_deconfliction` | **[M]** The deconfliction procedure remains live **throughout**. A blind phase never blinds deconfliction (§5.11) |

**Automatic expiry [M]:**

> **A blind phase expires automatically at `end`. It must not continue merely because nobody
> explicitly ended it.**

Extension requires a **new signature**, not silence. At expiry the phase is over regardless of
exercise state, and full disclosure to the blinded participants follows before the collaborative
validation session begins. **Blindness never extends into validation** — that session is where
the learning happens, and withholding there wastes the most expensive part of the program.

**Safety is never blind.** Safety observers, the deconfliction channel, stop conditions, and the
emergency contact roster operate at full visibility for the entire phase. A blind phase limits
*information about the test*, never *the ability to stop it*.

---

## 5.11 Deconfliction procedure **[M]**

Every test action must be attributable to this exercise **within 60 seconds** of a query.

| Mechanism | Detail |
|---|---|
| Exercise marker **[M]** | Standard string/tag in user agents, filenames, account names, ticket refs: `EX-YYYY-NNN` |
| Source infrastructure allow-list **[M]** | Registered in §5.7 and provided to SOC leadership before start |
| Deconfliction contact **[M]** | Name + phone + backup, available throughout the window |
| Deconfliction channel **[M]** | Dedicated channel; response SLA **≤ 5 minutes** |
| Answer key custody **[M]** | White holds the authoritative activity log; released on query, not preemptively (preserves the exercise) |
| Query procedure **[M]** | SOC analyst → SOC lead → deconfliction contact → White. Response format: **"exercise / not exercise / unknown-investigating"** |
| Default on ambiguity **[M]** | **Treat as a real incident and respond accordingly.** A wasted IR activation is cheap; a missed real intrusion is not. |
| Post-query handling | If declared "exercise," SOC continues to *practice* the response but suppresses external notifications and destructive containment. Record the fact and time of deconfliction. |

---

## 5.12 Emergency communication **[M]**

| Role | Name | Primary phone | Backup phone | Out-of-band channel | Availability |
|---|---|---|---|---|---|
| White Exercise Director **[M]** | | | | | |
| Deputy stop authority **[M]** | | | | | |
| Purple Lead **[M]** | | | | | |
| Lead operator **[M]** | | | | | |
| System Owner (per system) **[M]** | | | | | |
| SOC lead / on-call **[M]** | | | | | |
| CSIRT commander **[M]** | | | | | |
| Ops / on-call engineer **[M]** | | | | | |
| Legal **[M]** | | | | | |
| Privacy | | | | | |
| Executive Sponsor **[M]** | | | | | |

**[M] Contact roster tested by live call on ______ by ______.** A roster that has not been
tested within 5 business days of the exercise start is not a valid roster, and the exercise
does not start.

**[M] Out-of-band requirement:** at least one contact method must not depend on the corporate
network, corporate identity provider, or corporate messaging platform — because those are
exactly what an exercise may disrupt.

---

## 5.13 Stop conditions **[M]**

### Immediate automatic stop — no discussion, halt first, then notify
1. Unintended service degradation or outage of any production system
2. Unintended data modification, deletion, or exposure
3. Real security incident suspected anywhere in the environment
4. Safety concern of any kind
5. Loss of contact with the White Exercise Director or the deputy
6. Loss of control of test tooling, infrastructure, or an exercise identity
7. Encountering classified material, privileged communications, or unexpected regulated data
8. Any participant calls "STOP" — **no justification required at the time**
9. Third-party or customer impact of any kind
10. Test activity mistaken for a real incident and escalated externally (customers, regulators, law enforcement, insurers)
11. A required role's primary **and** backup are both unavailable
12. Legal, regulatory, or contractual concern raised by anyone

### Discretionary stop — White decides
- Findings so severe that continued testing adds risk without adding information
- Business events not anticipated during planning
- Exercise objectives already met
- Participant fatigue, or degraded ability to control the activity

### Stop procedure **[M]**
```
1. CALL      "STOP EXERCISE" in the exercise channel AND by phone to White
2. HALT      All operators cease activity immediately. Do not "finish this one step."
             Do not clean up yet -- preserve state for adjudication.
3. PRESERVE  Freeze and preserve current state and evidence
4. NOTIFY    White notifies System Owner, SOC lead, and Ops within 15 minutes
5. ASSESS    White determines: real incident? exercise-caused? unrelated?
6. DECIDE    White alone decides resume / modify / terminate
7. RECORD    Stop event, cause, decision, and rationale logged in the Decision Log
8. REPORT    Every stop appears in the AAR, including stops later found unnecessary
```

**No participant may resume activity on their own judgment, ever — including if they become
confident the concern was unfounded.** Resumption is a White decision, communicated explicitly.

**No-retaliation clause [M]:** calling an unnecessary stop is a correct action, always. It is
recorded as a healthy signal, never as a performance issue. Programs where people hesitate to
call stop are the programs that cause outages.

---

## 5.14 Rollback and recovery **[M]**

| Test case / change | Rollback procedure | Verified time to execute | Verified on (date) | Owner | Backup verified current |
|---|---|---|---|---|---|

**Rules [M]:**
- Every state-changing action has a documented, **timed**, and *previously executed* rollback.
- "Restore from backup" is only a rollback plan if a restore has actually been performed and
  timed within the last 90 days for that system.
- Backups for all in-scope systems verified within 24 hours before the window opens.
- Cleanup verification is performed by someone other than the operator who made the change [M].
- Residual artifacts (accounts, keys, files, rules, tickets, DNS records, cloud resources) are
  enumerated at creation, not reconstructed from memory at the end.

**Cleanup checklist (completed at close) [M]:** ☐ exercise identities revoked · ☐ tokens/keys
revoked · ☐ test files removed · ☐ configuration reverted · ☐ test infrastructure decommissioned
· ☐ temporary firewall/network rules removed · ☐ test data destroyed · ☐ tickets closed ·
☐ suppression rules removed · ☐ verified by (name, not the operator) ____ on ____

---

## 5.15 Third-party and supply-chain restrictions **[M]**

| Question | Answer |
|---|---|
| Third-party systems in scope? | ☐ No → skip section ☐ Yes → all fields mandatory |
| Provider name(s) | |
| Written authorization obtained **[M]** | ☐ Yes — attach. Provider's own testing-policy reference: ____ |
| Provider notification required/completed **[M]** | |
| Shared-responsibility boundary documented **[M]** | Exactly which layer is the customer's to test |
| Contractual clause permitting testing **[M]** | Contract §____ |
| Multi-tenant impact assessment **[M]** | Confirmation that no other tenant can be affected |
| Cloud provider policy compliance **[M]** | Confirm current provider penetration-testing policy; some services and techniques (notably DoS and control-plane abuse) are prohibited or require notice |
| Supply-chain / build-system testing | ☐ Not permitted ☐ Permitted in lab only ☐ Permitted with named approval |
| Open-source dependency testing | Test **your** use of the dependency. Never test upstream project infrastructure. |
| Findings disclosure to the provider **[M]** | Process and timeline; coordinated disclosure where the finding is in the provider's layer |

**Standing rule [M]:** absent written provider authorization, a third-party system is out of
scope. A SaaS "acceptable use" page is not authorization unless it explicitly permits customer
testing of the scope you intend.

---

## 5.16 Evidence handling **[M]**

| Requirement | Detail |
|---|---|
| Capture standard **[M]** | Every artifact: what, when (UTC), where from, by whom, method, tool + version |
| Integrity **[M]** | SHA-256 at capture; hash recorded in the Evidence Manifest before transfer |
| Chain of custody **[M]** | Every transfer/access logged: who, when, why |
| Storage **[M]** | Immutable/WORM where available; participant-write-restricted; custodian-controlled deletion |
| Access control **[M]** | Named individuals; access log reviewed by White at close |
| Marking **[M]** | Classification applied at capture, inherited from the highest-classified content |
| Retention **[M]** | Per §5.9 |
| Legal hold | Overrides destruction schedules; Legal notifies the Evidence Custodian |
| Screenshots/recordings | Faces, personal data, and unrelated content redacted at capture |
| **Prohibited [M]** | Evidence in personal storage, personal devices, personal accounts, general-purpose AI tools, or unmanaged chat |

---

## 5.17 Incident escalation **[M]**

| Trigger | Action | Who | Timeline |
|---|---|---|---|
| Suspected real incident during exercise | STOP → White adjudicates → CSIRT if real | Any participant | Immediate |
| Exercise activity caused an outage | STOP → rollback → System Owner + Ops | Operator + White | Immediate; owner notified ≤15 min |
| Real PII/PHI/CUI exposure | STOP → preserve → Privacy + Legal | Operator + White | ≤1 hour |
| Credential/secret discovered | Report → rotate | Operator → identity owner | ≤1 hour |
| Classified spillage suspected | STOP → do not investigate → security officer per spillage procedure | Any participant | Immediate |
| Third-party impact | STOP → Legal + vendor manager | White | ≤1 hour |
| Exercise mistaken for a real attack, escalated externally | STOP → White deconflicts → correct the record | White | Immediate |
| Regulatory notification threshold met | Legal decides; White provides facts | Legal | Per statute |
| **Finding of active, real compromise unrelated to the exercise** | **STOP the exercise; CSIRT takes primacy; exercise evidence is preserved separately and may be needed** | White | Immediate |

---

## 5.18 Legal, privacy, and final sign-off **[M]**

### Reviews
| Review | Reviewer | Date | Outcome | Conditions |
|---|---|---|---|---|
| Legal review **[M]** | | | ☐ Approved ☐ Approved w/ conditions ☐ Denied | |
| Privacy review **[M]** | | | ☐ Approved ☐ Approved w/ conditions ☐ Denied | |
| Safety review (where applicable) | | | | |
| Contracts/CO review (P3) | | | | |
| Insurance/regulatory notification | | | | |

### Signatures — **all required before any activity [M]**
| Role | Name | Signature | Date (UTC) |
|---|---|---|---|
| White Exercise Director | | | |
| Purple Team Lead | | | |
| System Owner — system 1 | | | |
| System Owner — system 2 | | | |
| Legal Counsel | | | |
| Privacy Officer | | | |
| Safety Officer (if applicable) | | | |
| Executive Sponsor (required for production scope) | | | |
| Lead operator (acknowledgement of prohibited actions §5.6) | | | |

### Operator acknowledgement **[M]**
> *I have read this Rules of Engagement document in full. I understand the scope limits, the
> prohibited actions in §5.6, the stop conditions in §5.13, and the data-handling rules in §5.9.
> I will not take any action outside this authorization. I understand that any participant may
> call STOP, that I must halt immediately when a stop is called, and that only the White
> Exercise Director may authorize resumption.*

Each named operator signs individually. A team-lead signature does not cover the team.

---

## 5.19 Closure record **[M]**

| Item | Status | Verified by | Date |
|---|---|---|---|
| All activity ceased | ☐ | | |
| Exercise identities revoked | ☐ | | |
| Test infrastructure decommissioned | ☐ | | |
| Artifacts removed and cleanup verified (by non-operator) | ☐ | | |
| Test data destroyed; certificate issued | ☐ | | |
| Evidence manifest complete and hashed | ☐ | | |
| Deconfliction record closed | ☐ | | |
| Findings entered into the system of record | ☐ | | |
| AAR scheduled | ☐ | | |
| RoE archived per retention schedule | ☐ | | |

**Exercise formally closed by (White Exercise Director):** ______________ **Date:** ________
