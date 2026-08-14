# ORANGE TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> **Standing constraint, above everything else in this playbook:** Orange operates in design
> documents, lab, and pre-production. Not production. The constraint is not a limitation on the
> role — it is what makes an offensive person safe to embed with builders, and therefore what
> makes the role possible at all.

---

## 1. Workflow stages Orange owns

| Stage | Orange's role | Gate |
|---|---|---|
| 5 · Threat modeling | **A** (facilitates; Yellow owns the content) | Model produced *with* engineers, never *for* them |
| 6 · Test-case development | R — abuse-case-derived cases | |
| 7 · Safety validation | R — technical review | |
| 11 · Remediation | C — regression test co-authorship | Regression tests are **safe** — checks, not exploits |
| 16 · Lessons learned | R — design patterns | Systemic lessons → attack-path catalog |

---

## 2. Weekly rhythm

| Day | Activity |
|---|---|
| Mon | Design review queue triage; identify what is about to be architecturally frozen |
| Tue–Wed | Threat modeling sessions (2–4 h each, with the building team) |
| Thu | Pre-production validation in the authorized envelope; regression test development |
| Fri | Office hours / design review clinic; attack-path catalog maintenance |
| Monthly | Developer education session, built from a real finding from the last 30 days |
| Quarterly | Red Team rotation (1–2 weeks embedded, or an operator embedded with Orange) |

---

## 3. Runbook — facilitating a threat model

The core skill of the role. **The document is a byproduct; the knowledge transfer is the point.**

```
BEFORE
  - Read the design first. Arriving unprepared wastes the engineers' 3 hours.
  - Identify the crown-jewel data and where it lives.
  - Bring ONE relevant real-world example. Not a lecture -- an anchor.

DURING  (2-4 hours, whiteboard, engineers holding the pen wherever possible)
  1. WHAT ARE WE BUILDING?
     Let them draw it. Their diagram, however rough, beats your accurate one --
     you are testing whether they can articulate the system, and gaps in their
     drawing are findings.
  2. WHAT CAN GO WRONG?
     STRIDE per element, or attack trees for a focused concern.
     ASK, don't tell: "what stops me from calling this endpoint as another tenant?"
     Silence after a question is fine. Wait it out. The answer they reach
     themselves is the one they remember.
  3. WHAT ARE WE GOING TO DO ABOUT IT?
     Every path: mitigate / transfer / accept / eliminate. Named owner. Work item.
  4. DID WE DO A GOOD JOB?
     What did we skip? What are we assuming is secure?
     Most missed attack paths live in the unstated assumptions.

AFTER
  - THEY own the document; it lives with the code.
  - Instrumentation gaps -> Green ("to detect path X we need source S").
  - Abuse cases -> their backlog as requirements.
  - Attack paths -> your internal attack-path catalog.

NEVER
  - Write the model alone and present it. It will be stale in a month and nobody
    will refresh it, because nobody owns it.
  - Say "that's insecure." Say "here is how I would attack it; what stops me?"
  - Win the room. If engineers leave feeling stupid, they will not invite you back,
    and shift-left dies quietly.
```

---

## 4. Runbook — design review

```
TRIGGER   Above-threshold system, or a material architecture change.
          Engage BEFORE architecture freeze. Being invited after freeze is
          a PROCESS failure -- fix the gate, do not just work harder.

FOCUS     - Trust boundaries: where does untrusted data cross into trusted code?
          - Identity: what can each human and workload identity actually reach?
          - Blast radius: if one component is compromised, what else falls?
          - Assumptions: what is assumed secure that has not been verified?
          - Recoverability: what does an attacker have to do to make this unrecoverable?

OUTPUT    Design Review Record: paths found, recommendations, owner decision.
          Orange RECOMMENDS. Orange does not block. The Green defensibility gate
          blocks; the System Owner accepts risk. Keep the distinction crisp --
          it is what keeps you welcome in the room.

IF IGNORED  Record the recommendation and the decision verbatim. If the same
            unaddressed path later appears as a Purple finding, the record shows
            it was raised. That is a GOVERNANCE escalation, not an Orange failure --
            do not treat it as a personal defeat, and do not say "I told you so."
```

---

## 5. Runbook — safe regression tests

Every discovered weakness class should become a test that runs forever. **Safe means: proves the
weakness is absent without performing an attack.**

| Weakness class | Safe regression test | Not this |
|---|---|---|
| Cross-tenant data access | Integration test: authenticated as tenant A, request tenant B's object → assert 403 | An exploit script that retrieves tenant B's data |
| Over-permissive workload identity | Policy-as-code: fail the build if role assignments exceed the allow-list | A privilege-escalation chain run in CI |
| Missing authentication on an endpoint | Contract test: unauthenticated request → assert 401 | A scanner sweeping production |
| Secret in code | Secret scanning in CI with the specific pattern | Manual review |
| Vulnerable dependency reintroduced | SCA gate pinned to the fixed version | Periodic manual check |
| Missing security header / TLS config | Automated config assertion against pre-prod | Nothing |
| Logging removed by a refactor | Test asserting the security event is emitted with required fields | Hoping Green notices |

**Rules [M]:** runs in CI · deterministic · fast enough that nobody disables it · fails loudly
with a message that says what to fix · **contains no exploitation, no credential material, no
payloads.** A regression test that has to be disabled to ship is a regression test that will be
deleted.

---

## 6. Runbook — teaching

Monthly, 45 minutes, built from a real finding from the last 30 days.

```
1. Show the DESIGN DECISION, not the vulnerability.
   "Someone chose to pass the tenant ID from the client. Here's why that was
    reasonable at the time."
2. Walk the attack path step by step. Slowly. Let them see it coming.
3. Show the fix, and what it costs.
4. Show the regression test that stops it returning.
5. Ask: "where else in our estate does this pattern exist?"
   This question routinely finds more than the original exercise did.

NEVER  use a real team's mistake as an example without their consent and
       without them present. Once you do that, nobody will tell you anything again.
```

---

## 7. Hard boundaries — non-negotiable

| Situation | Required action |
|---|---|
| Discover an actively exploitable **production** issue | **Report to CSIRT immediately. Do not exploit it to prove the point.** (SoD-7) |
| Asked to "just check" something in production | Refuse. Route through White + System Owner + RoE. |
| Tempted to test an unauthorized environment | No. Scope is an allow-list, always. |
| Offered production credentials | Decline. Orange uses lab-only synthetic identities. |
| Asked to perform the compliance penetration test | Decline and explain: Orange is integrated with the builders and cannot provide independent-assessment evidence (crosswalk conflict F-1). Recommend an independent assessor. |
| Find an issue in a third-party product | Coordinated disclosure through Legal and vendor management. Never independently. |

**If an Orange action ever causes a production incident, the charter is reviewed and White
investigates.** That consequence is deliberate and it is what earns the trust that makes
embedding possible.

---

## 8. Metrics Orange owns

M-14 threat model coverage · **shift-left ratio** (issues found by Orange at design/pre-prod ÷
issues found by Purple later — rising is good) · % of Purple findings tracing to a
previously-flagged Orange recommendation (**low is good**) · % of weakness classes with a safe
regression test in CI · developer-reported usefulness of design reviews.

**The shift-left ratio is the metric that justifies the role.** A design-stage fix costs a
conversation; the same issue found in production costs an exercise, a finding, a sprint, a
retest, and sometimes an incident.

---

## 9. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Threat models written *for* teams | Facilitate; they hold the pen; they own the document |
| Invited after architecture freeze | Fix the process gate, not your working hours |
| Blocking releases directly | Recommend; Green's gate blocks; the System Owner accepts risk |
| Exploiting to prove a point | Report; the proof is the analysis, not the compromise |
| Producing "independent" assessment evidence | You are not independent by design — say so plainly |
| Regression tests that are actually exploits | Assertions, not attacks |
| Winning arguments | If they stop inviting you, your technical accuracy stopped mattering |
