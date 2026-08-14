# §11 — Compliance Crosswalk

← [Index](../README.md) · Prev → [§10 AI](09_ai_and_automation_governance.md) · Next → [§12 Roadmap](11_implementation_roadmap.md)

---

## 11.0 What this section does and does not claim **[M] — read first**

**This operating model does NOT create compliance, certification, or authorization.**

| It produces | It does not produce |
|---|---|
| Evidence artifacts that assessments consume | An ATO, ATC, or authorization to operate |
| Control implementation for a *subset* of controls | A CMMC certification (only a C3PAO/DIBCAC assessment does) |
| Continuous-monitoring inputs | A FedRAMP authorization (only the PMO/agency process does) |
| Assessment support and readiness | An ISO 27001 certificate (only an accredited certification body does) |
| Documented residual-risk decisions | A SOC 2 report (only a licensed CPA firm does) |

**The mappable subset is small.** For a typical NIST SP 800-53 moderate baseline of ~300+
controls, this model directly evidences roughly **40–70 controls** — the assessment, testing,
monitoring, incident-response-testing, and secure-development families. It touches many more
indirectly. **Presenting this as "we cover X% of the framework" is a misrepresentation**
(see metric M-16's qualifier).

**Verification required before use [M]:** framework versions and requirements change. Confirm
current text with your assessor/auditor before relying on any row below. Specifically flagged:
Open Decisions **O-3** (governing framework), **O-15** (HIPAA Security Rule NPRM status), and
**O-16** (FedRAMP program baseline and current Penetration Test Guidance version).

---

## 11.1 The five evidence layers — keep these separate

Auditors reject evidence that conflates these. Every artifact this model produces belongs to
exactly one layer.

| Layer | Definition | Produced by | Example artifact |
|---|---|---|---|
| **L1 — Technical control implementation** | The control actually exists and functions | Green (detections, hardening, identity, backup), Yellow (code, IaC, CI/CD) | Detection content in Git; hardening baseline; conditional access policy export |
| **L2 — Assessment evidence** | Independent verification that the control works | Purple (validation), external assessor (independent testing) | Retest Record; six-stage outcome table; independent pentest report |
| **L3 — Governance approval** | Authorized humans decided this | White (RoE, authorization), System Owners | Signed RoE; Authorization Record; AAR |
| **L4 — Continuous monitoring** | Ongoing, not a point-in-time snapshot | Green (telemetry health), Purple (recurring validation), SOC | M-10 telemetry availability; recurring exercise schedule; detection catalog changelog |
| **L5 — Residual-risk acceptance** | What is knowingly not fixed, by whom, until when | System Owner (signs), GRC (registers) | Risk Acceptance with expiry; risk register entry; POA&M line |

**[M] Never present L2 evidence produced by Orange as independent assessment.** Orange is
integrated with the builders by design; several frameworks require assessor independence.
Relabeling integrated testing as independent assessment is an audit finding waiting to happen —
and, in a federal context, potentially a false-statement exposure.

---

## 11.2 NIST CSF 2.0 — organizing spine

CSF 2.0 is the recommended organizing spine (Open Decision O-3 default) because it maps outward
to everything else and includes the **GOVERN** function that this model's White Team implements.

| CSF 2.0 Function | Category (illustrative) | Model contribution | Layer |
|---|---|---|---|
| **GOVERN (GV)** | GV.OC, GV.RM, GV.RR, GV.PO, GV.OV, GV.SC | White charter; authorization; RACI; risk acceptance; third-party test restrictions | L3, L5 |
| **IDENTIFY (ID)** | ID.AM, ID.RA, ID.IM | Threat models (Orange/Yellow); attack-surface inventory; risk-driven scenario selection; lessons learned | L1, L2 |
| **PROTECT (PR)** | PR.AA, PR.DS, PR.PS, PR.IR | Identity controls, hardening, segmentation, paved roads (Green); secure development (Yellow) | L1 |
| **DETECT (DE)** | DE.AE, DE.CM | Detection engineering (Green); telemetry (Green); validated detection coverage (Purple) | L1, L2, L4 |
| **RESPOND (RS)** | RS.MA, RS.AN, RS.CO, RS.MI | IR exercised and measured (MTTC); SOAR playbooks; deconfliction discipline | L1, L2 |
| **RECOVER (RC)** | RC.RP, RC.CO | Restore drills with measured RTO/RPO (Green) | L1, L2 |
| **ID.IM (Improvement)** | ID.IM-01..04 | **The core of this model** — exercises, incidents, and lessons drive documented improvement | L2, L4 |

---

## 11.3 NIST SP 800-53 Rev 5 — control mapping

| Control | Title | Model contribution | Layer | Owner |
|---|---|---|---|---|
| **CA-2** | Control Assessments | Purple exercise program as recurring assessment activity | L2 | Purple + GRC |
| **CA-2(1)** | Independent Assessors | **Requires independence** — external assessor or an internal Red Team outside the builder chain. Orange does **not** satisfy this. | L2 | GRC |
| **CA-5** | Plan of Action & Milestones | Findings → remediation tickets → POA&M lines with owners and dates | L5 | GRC + System Owner |
| **CA-7** | Continuous Monitoring | Recurring exercise cadence + telemetry health (M-10) + detection catalog currency | L4 | Green + Purple |
| **CA-8** | Penetration Testing | Authorized testing under RoE | L2 | Purple/Red |
| **CA-8(1)** | **Independent Penetration-Testing Agent or Team** | Requires an *independent penetration-testing* relationship — distinct from CA-2(1)'s independent *control assessor*. See §11.14 | L2 | Red (position-dependent) |
| **CA-8(2)** | Red Team Exercises | Adversary emulation with defined rules of engagement | L2 | Purple/Red |
| **RA-3** | Risk Assessment | Threat-informed scenario selection tied to the risk register | L2 | GRC |
| **RA-5** | Vulnerability Monitoring & Scanning | Vulnerability management + validation that findings are real | L1, L2 | Yellow + Green |
| **RA-7** | Risk Response | Risk acceptance with expiry; remediation decisions | L5 | System Owner |
| **IR-3** | Incident Response Testing | Purple exercises exercising the IR process end to end | L2 | Purple + CSIRT |
| **IR-3(2)** | Coordination with Related Plans | Deconfliction; White coordination across IR, ops, comms plans | L3 | White |
| **IR-4** | Incident Handling | Measured MTTI/MTTC from exercises | L1, L2 | CSIRT |
| **SI-4** | System Monitoring | Detection engineering and telemetry | L1 | Green |
| **SI-4(2)(4)(11)** | Automated tools, inbound/outbound traffic, anomalous behavior | Detection content and validation | L1, L2 | Green + Purple |
| **AU-6** | Audit Review, Analysis, Reporting | SOC triage measured in six-stage validation (stage 4) | L1, L2 | SOC |
| **AU-9** | Protection of Audit Information | Evidence integrity; WORM store; chain of custody | L1, L3 | White |
| **CM-3** | Configuration Change Control | Remediation changes flow through normal change control | L1 | Yellow |
| **CM-6** | Configuration Settings | Hardening baselines + drift measurement | L1 | Green |
| **SA-8** | Security & Privacy Engineering Principles | Secure-by-design requirements; paved roads | L1 | Green + Yellow |
| **SA-11** | Developer Testing & Evaluation | Yellow security testing in CI | L1, L2 | Yellow |
| **SA-11(2)** | Threat Modeling & Vulnerability Analyses | **Orange's core contribution** | L1, L2 | Orange |
| **SA-11(5)** | Penetration Testing | Pre-production validation (Orange) + independent testing (Red/external) | L2 | Orange / Red |
| **SA-15** | Development Process, Standards, Tools | Secure SDLC, SBOM, CI/CD security | L1 | Yellow |
| **SR-3 / SR-5 / SR-11** | Supply Chain Controls / Acquisition Strategies / Component Authenticity | SBOM, provenance, dependency management, build-system review | L1 | Yellow + Orange |
| **CP-4** | Contingency Plan Testing | Restore drills with measured RTO/RPO | L2 | Green |
| **CP-9 / CP-10** | System Backup / Recovery | Backup verification and restore validation | L1, L2 | Green |
| **PM-14** | Testing, Training, Monitoring | Program-level integration of testing with training | L3, L4 | CISO + White |
| **AT-2 / AT-3** | Literacy / Role-Based Training | Exercise-derived training; Security Champion curriculum | L1 | Yellow + HR |

---

## 11.4 NIST SP 800-171 / CMMC 2.0

**⚠ Flagged conflict — resolve via O-3.** NIST SP 800-171 exists in Revision 2 (`3.12.1`-style
numbering) and Revision 3 (`03.12.01`-style, reorganized). CMMC practice identifiers were built
on the Rev 2 mapping. **Which revision your contract requires is a contractual question, not a
technical one** — confirm with your contracting officer before mapping evidence. Do not maintain
two mappings; pick the contractually required one and note the other.

| Requirement family | Model contribution | Layer |
|---|---|---|
| **Security Assessment (3.12.x / 03.12.xx)** — periodic assessment, POA&M, continuous monitoring | Exercise program, findings→POA&M, recurring validation | L2, L4, L5 |
| **Risk Assessment (3.11.x / 03.11.xx)** — risk assessment, vulnerability scanning | Threat-informed selection, vulnerability validation | L2 |
| **Incident Response (3.6.x / 03.06.xx)** — IR capability and **IR testing** | Purple exercises are the IR test; measured MTTC | L2 |
| **Audit & Accountability (3.3.x / 03.03.xx)** | Telemetry, log review measured in stage 4 | L1, L2 |
| **System & Information Integrity (3.14.x / 03.14.xx)** — monitoring | Detection engineering + validation | L1, L2 |
| **Configuration Management (3.4.x / 03.04.xx)** | Hardening baselines, drift, change control | L1 |
| **Identification & Authentication (3.5.x / 03.05.xx)** | Identity controls (Green) validated by Purple | L1, L2 |

**CUI-specific requirements this model must respect [M]:**
- Exercise evidence containing CUI is itself CUI — marked, stored in the authorized boundary,
  and never placed in general-purpose tooling or unapproved AI systems
- Contractor personnel performing testing must be authorized under the contract (**CO/COR
  verification is a mandatory RoE step at P3**)
- CUI encountered during testing is not collected (RoE §5.9)

---

## 11.5 RMF (NIST SP 800-37)

| RMF Step | Model contribution | Layer | Caution |
|---|---|---|---|
| Prepare | Asset inventory, threat models, system criticality | L1 | |
| Categorize | Data classification informs scope and RoE handling | L3 | Model consumes categorization; it does not perform it |
| Select | Threat models inform control selection (Orange → Yellow/Green) | L1 | |
| Implement | Green and Yellow implement | L1 | |
| **Assess** | Purple validation is **supporting** evidence; the formal assessment is performed by an independent assessor | L2 | **Purple validation ≠ Security Assessment Report** |
| **Authorize** | The AO authorizes. This model provides evidence and residual-risk documentation. | L3, L5 | **Nothing here produces an ATO** |
| **Monitor** | Continuous validation, telemetry health, recurring exercises = strong ConMon inputs | L4 | Often the highest-value RMF contribution of this model |

---

## 11.6 FedRAMP

**⚠ Verify against O-16 before use.** The FedRAMP program has been undergoing significant change;
confirm the current baseline set and the current Penetration Test Guidance version with the PMO
or your 3PAO before scoping anything.

| Requirement area | Model contribution | Layer | Caution |
|---|---|---|---|
| Annual assessment | Evidence for the 3PAO; readiness | L2 | **Only a 3PAO's assessment counts.** Internal testing is preparation. |
| Penetration testing per FedRAMP guidance (defined attack vectors incl. external/internal, tenant-to-tenant, mobile/client, and social engineering as applicable) | Purple scenarios can be aligned to the same vectors for readiness | L2 | The required test must be performed by the independent assessor |
| Continuous monitoring (monthly reporting, POA&M) | Findings → POA&M; telemetry health; recurring validation | L4, L5 | |
| Significant change assessment | Orange design review + Purple validation on material change | L2 | Notify per FedRAMP significant-change process |
| Incident response | Exercised IR with measured times; US-CERT/agency reporting timelines rehearsed | L2 | Reporting obligations are contractual — rehearse them in exercises |

---

## 11.7 DISA STIGs / SRGs

| Area | Model contribution | Layer |
|---|---|---|
| STIG-compliant baselines | Green owns baselines derived from applicable STIG/SRG; drift measured | L1 |
| STIG validation | Automated checks; Purple validates that non-compliance is *detectable*, not just present | L1, L2 |
| Documented deviations | Deviations → risk acceptance with expiry | L5 |
| Security tooling itself STIG'd | The tools in [§9](08_toolchain_architecture.md) are in scope for hardening too | L1 |

---

## 11.8 ISO/IEC 27001:2022

| Annex A control | Model contribution | Layer |
|---|---|---|
| **A.5.7** Threat intelligence | CTI → prioritized techniques → exercises | L1, L4 |
| **A.5.24–5.28** Incident management (planning, assessment, response, evidence) | Exercised IR; **evidence collection discipline maps directly to A.5.28** | L1, L2 |
| **A.5.35** Independent review of information security | White independence + independent assessment | L2, L3 |
| **A.5.19–5.23** Supplier & cloud service security | Third-party test restrictions (RoE §5.15); supply-chain review | L1, L3 |
| **A.8.8** Management of technical vulnerabilities | Vulnerability management + validation + remediation SLA | L1, L2 |
| **A.8.16** Monitoring activities | Detection engineering; telemetry | L1 |
| **A.8.25–8.29** Secure development lifecycle, security requirements, secure architecture, secure coding, security testing | Yellow + Orange, end to end | L1, L2 |
| **A.8.31** Separation of dev/test/prod | Environment restrictions in RoE §5.8 | L1, L3 |
| **Clause 9.2 / 9.3 / 10** Internal audit, management review, improvement | AAR + lessons learned + metrics feed management review | L2, L4 |

---

## 11.9 SOC 2 (TSC 2017, with points of focus)

| Criterion | Model contribution | Layer |
|---|---|---|
| **CC3.2** Risk identification and analysis | Threat models; risk-driven scenario selection | L2 |
| **CC4.1** Evaluations to ascertain whether controls are functioning | **The single best fit** — Purple validation is exactly this | L2 |
| **CC5.x** Control activities / technology general controls | Green and Yellow implementation | L1 |
| **CC7.1** Detect and monitor for new vulnerabilities/config changes | Vulnerability management + drift monitoring | L1 |
| **CC7.2** Monitor for anomalies indicative of malicious acts | Detection engineering + validated coverage | L1, L2 |
| **CC7.3 / CC7.4** Evaluate and respond to security events | Measured MTTI/MTTC from exercises | L2 |
| **CC7.5** Recover from identified incidents | Restore drills; recovery validation | L2 |
| **CC8.1** Change management | Remediation via normal change control | L1 |
| **CC9.1** Risk mitigation activities | Risk acceptance with expiry; compensating controls | L5 |

**Type II note:** SOC 2 Type II tests operating effectiveness *over a period*. A recurring
exercise cadence with dated artifacts is far stronger evidence than a single annual test — this
model naturally produces period evidence.

---

## 11.10 HIPAA Security Rule

**⚠ Verify status — see Open Decision O-15.** A 2025 NPRM proposed prescriptive testing
requirements (annual penetration testing, semiannual vulnerability scanning) that would change
this mapping materially if finalized. Confirm the operative rule text with counsel.

| Provision | Model contribution | Layer |
|---|---|---|
| §164.308(a)(1)(ii)(A) Risk analysis | Threat models + validated exploitability inform real risk, not theoretical risk | L2 |
| §164.308(a)(1)(ii)(B) Risk management | Remediation program with SLAs | L1, L5 |
| §164.308(a)(6) Security incident procedures | Exercised IR with measured response | L1, L2 |
| §164.308(a)(8) Evaluation (periodic technical and non-technical) | **Primary fit** — recurring exercises are periodic technical evaluation | L2 |
| §164.312(b) Audit controls | Telemetry and log review | L1 |

**[M] ePHI is never accessed, viewed, copied, or exfiltrated during testing** (RoE §5.9). A
testing program that exposes PHI creates the breach it was meant to prevent.

---

## 11.11 PCI DSS v4.x

| Requirement | Model contribution | Layer | Caution |
|---|---|---|---|
| **6.x** Secure development | Yellow secure SDLC, code review, dependency management | L1 | |
| **11.3.x** Vulnerability scanning (internal/external) | Vulnerability management; ASV scans are separate and must be performed by an Approved Scanning Vendor | L1, L2 | **ASV scans cannot be performed internally** |
| **11.4.x** Penetration testing (methodology, internal, external, on significant change) | Purple/Red testing aligned to the documented methodology | L2 | Confirm assessor-independence expectations with your QSA |
| **11.4.x** Segmentation testing (where segmentation isolates the CDE) | Green designs segmentation; Purple validates it; frequency differs for merchants vs. service providers — **confirm your obligation** | L1, L2 | |
| **11.5.x** Change/tamper detection, intrusion detection | Detection engineering + validation | L1, L2 | |
| **12.10.x** Incident response plan, testing, review | Exercised IR; annual review evidenced by AARs | L2 | |

**[M] Cardholder data is never accessed during testing.** If encountered, stop that test case and
notify White and the CDE owner (RoE §5.9).

---

## 11.12 Framework conflicts to flag to leadership

| # | Conflict | Impact | Recommended resolution |
|---|---|---|---|
| **F-1** | **Independence.** "Independence" is four different requirements wearing one word. Conflating them is how integrated testing gets mislabelled as independent assessment. | Evidence rejected, or — in a federal context — a false-statement exposure | **PARTIALLY RESOLVED 2026-08-14. See the four-way taxonomy in §11.14 below.** Red closes the *internal technical-assessment* gap only. It does **not** satisfy independent exercise scoring where Red participated, nor external organizational-assessor requirements. |
| **F-2** | **Testing frequency.** Frameworks specify different cadences (annual, semiannual, on significant change, continuous). | Confusion about "are we compliant?" | Adopt the **strictest applicable** cadence per system and record the driver per system in the GRC platform |
| **F-3** | **800-171 Rev 2 vs Rev 3 numbering** while CMMC references the older mapping | Duplicate mappings, evidence mismatch at assessment | Confirm the contractually required revision with the contracting officer (O-3); maintain one mapping |
| **F-4** | **Retention.** 7-year security retention vs. privacy-law data-minimization obligations | Direct conflict for evidence containing personal data | Minimize at capture so the conflict rarely arises; where it does, Legal + Privacy decide per artifact and record the decision |
| **F-5** | **Production testing.** Some frameworks expect production-representative testing; safety and availability constraints push testing to pre-prod | Evidence may be challenged as non-representative | Document environment equivalence; test in production **for detection validation** (observational, low risk) even where exploitation stays in pre-prod |
| **F-6** | **Cloud provider policies** may prohibit techniques a framework expects you to test | Untestable requirement | Document the provider restriction as a scoping limitation in the assessment; test the customer-responsibility layer thoroughly |
| **F-7** | **Regulator/customer notification** obligations may be triggered by *simulated* incidents under some contracts and insurance policies | Accidental notification obligation, or voided coverage | Legal review in every RoE (§5.18); pre-agree simulation-notification language at contract and policy renewal (O-14) |
| **F-8** | **AI systems** are ahead of most control frameworks — several have no explicit prompt-injection or agent-privilege controls | Real risk with no control to map to | Map to secure-development and monitoring controls (SA-11, SA-15, SI-4, A.8.25–8.29); document the gap explicitly rather than pretending coverage exists |

---

## 11.14 The four kinds of independence **[M]**

Governance decision, program owner, 2026-08-14. **"Independent" is not one property.** Establish
which kind a requirement actually demands before assigning it to a function.

| Independence | Appropriate function | Condition |
|---|---|---|
| **Independent from development** | **Red** | Satisfied if Red does not report through Yellow or Orange |
| **Independent from defense operations** | **Red** | Satisfied if Red does not operate or own Blue's controls |
| **Independent exercise scoring** | **Internal Audit / [Exercise Assurance](18_exercise_assurance.md)** | **Red cannot satisfy this for an exercise in which Red participated** |
| **Independent organizational assessment** | **External assessor** — 3PAO, C3PAO, QSA, or the assessor the framework names | Required whenever the framework demands organizational independence. No internal function satisfies it |

### The statement of record

> **Red closes the internal technical-assessment independence gap where organizational and
> framework requirements permit internal assessment. Red does not satisfy independent exercise
> scoring when Red participated, nor external organizational-assessor requirements such as 3PAO,
> C3PAO, or QSA independence.**
>
> **Orange remains intentionally embedded with engineering and must not issue an independent
> assurance opinion.**

### Three controls, three different required relationships **[M]**

These are routinely treated as one requirement. They are not. **The relationship each control
demands is different, so the same Red Team evidence satisfies different controls depending on
Red's organizational position and contractual role.**

| Control | Required relationship |
|---|---|
| **CA-2(1)** | **Independent control assessor** |
| **CA-8(1)** | **Independent penetration-testing agent or team** |
| **SA-11(5)** | **Developer-performed or developer-provided** penetration testing |

**CA-2(1)** requires assessors impartial and free from actual or perceived conflicts concerning
system development, operation, management, or determining control effectiveness. **Whether Red
qualifies depends on the assessment context and the authorizing authority** — confirm with the
AO; do not assume.

**SA-11(5)** is **unqualified with respect to assessor independence, but not unconditionally
satisfied.** It requires the *developer* of the system, component, or service to perform
penetration testing at an organization-defined rigor and under organization-defined constraints.
It does not impose CA-2(1)'s independence requirement — but the evidence must still establish
that **the developer performed or contractually provided** the testing as required. Red running a
test does not by itself satisfy SA-11(5) unless Red occupies the developer-provided role for that
system.

> **Red can support all three technically. Organizational position, contractual role, and
> independence determine which control its evidence actually satisfies.**
> Determine that per system, record it, and do not carry the determination across systems.

### Applying it

| Requirement | Who can satisfy it |
|---|---|
| **FedRAMP** annual assessment / pentest | **3PAO only.** Red produces readiness evidence, not the assessment |
| **PCI DSS 11.4** penetration testing | Confirm assessor-independence expectations with your QSA; internal is permitted under conditions, and the QSA decides |
| **CMMC** assessment | **C3PAO / DIBCAC.** Red is preparation |
| **Exercise score** for any exercise Red joined | **Exercise Assurance** — never Red, never White for its own performance |

### Three evidence streams, never merged in a report
1. **Integrated testing** — Orange, Purple. Layer L1/L2 **supporting**.
2. **Internal independent assessment** — Red. Layer L2 **formal**, where internal assessment is permitted.
3. **External organizational assessment** — 3PAO/C3PAO/QSA. Layer L2 **formal**, where the framework demands it.

**Relabelling stream 1 or 2 as stream 3 is the failure this taxonomy exists to prevent.**

---

## 11.13 Evidence-to-control mapping procedure **[M]**

1. GRC maintains the authoritative control-to-artifact mapping in the GRC platform — not in a
   spreadsheet, and not in this document (this document goes stale; the platform is operational).
2. Every artifact carries its control references in metadata at creation, not retrofitted before
   an audit.
3. Evidence freshness is tracked per control; expired evidence surfaces as a control gap in M-16.
4. **Never map the same artifact to a control in a way that overstates it.** A detection
   validation result evidences that a *specific* technique is detected, not that SI-4 is
   satisfied in full.
5. Quarterly, GRC samples 10% of mappings and verifies that the artifact actually supports the
   claim. Record the sample results — this is itself evidence of a functioning control
   environment.
