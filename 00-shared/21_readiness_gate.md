# §22 — Assessment Readiness Gate and State Model

← [Index](../README.md) · Related → [§21 Closure Plan](20_closure_plan.md) · [§18 Assessment](17_capability_assessment.md) · [§19 Exercise Assurance](18_exercise_assurance.md)

**Authority:** program owner decision, 2026-08-14.
**Automated issuance gate (`PROGRAM-READINESS-GATE-001`):** [`config/assessment_readiness.json`](config/assessment_readiness.json)

---

## 22.1 Current program state

> ## `PREREQUISITES_PENDING`
>
> **Status:** `NOT_ASSESSMENT_READY`
> **Every result produced in this state is marked `TRAINING_OR_ENGINEERING_USE_ONLY`.**

The design is structurally coherent and audit-defensible **by design**. It is **not yet
assessment-ready operationally**. Those are different claims and the system must not conflate
them.

| Permitted now | Not permitted now |
|---|---|
| ✅ Run exercises | ❌ Issue an assurance statement |
| ✅ Compute diagnostic scores | ❌ Present any score as assurance |
| ✅ Engineering rehearsal and training | ❌ Forward results to an auditor, regulator, customer, or board |

**This distinction is the point.** It lets you rehearse before full readiness without letting the
rehearsal results become apparent assurance evidence — which is how organizations accidentally
build a compliance narrative on a training run.

---

## 22.2 The four required gates

Evaluation is **`all`** — every gate must hold. There is no partial credit and no weighted
version of readiness.

| Gate | Closure item | Owner | Holds when |
|---|---|---|---|
| `canonical_implementation_selected` | 1 (R-8) | Owner / ATLAS | One canonical path declared; the other archived; **CI rejects duplicate package identities** |
| `exercise_assurance_operational` | 3 | Exec Sponsor + Internal Audit | Performer named and COI-screened; holds the assessment key; EA-6 line confirmed **in writing** |
| `key_custody_verified` | 2 (R-10) | White + CISO | Authorization key in HSM/secret manager; **IAM denial verified by attempting access as Red and being denied**; evidence key split; revocation tested end to end |
| `containment_verified_all_supported_platforms` | 4 (R-6) | Red Lead | Path-escape test passes on **Linux CI and Windows**; **CI treats a skip as a failure** |

Full verification criteria are in the [config](config/assessment_readiness.json) — machine-readable
so that "we think we're ready" cannot substitute for evidence.

---

## 22.3 The state model

```
DESIGN_COMPLETE
      |   charters, RACI, gates, scorecards, trust model ratified
      v
PREREQUISITES_PENDING            <-- YOU ARE HERE
      |   ALL FOUR required gates verified with evidence
      v
ASSESSMENT_READY
      |   signed RoE · safety assessment approved · contact roster live-tested
      |   · inject commitment published
      v
EXERCISE_AUTHORIZED
      |   execution finished or terminated · cleanup verified by a non-operator
      v
EXERCISE_COMPLETE
      |   Exercise Assurance validates evidence completeness and integrity
      |   · ledger verifies and seals
      v
EVIDENCE_VERIFIED
      |   scores computed against the FROZEN rubric · signed with the assessment key
      v
ASSESSMENT_ISSUED
```

### The rule that makes it worth having **[M]**

> **No state may be skipped merely because test suites are green.**

A passing test suite is evidence about *code*. A state transition is a claim about *the
program* — that custody exists, that an independent assessor exists, that containment has been
demonstrated on every platform it runs on. Green tests have never established any of those.

### Regression triggers

The program **returns to `PREREQUISITES_PENDING`** if any of these occur — automatically, not by
committee:

- Any required gate ceases to hold
- A signing key is found outside its designated custody
- Canonical-implementation ambiguity is reintroduced
- The Exercise Assurance performer becomes unavailable or conflicted

Regression is not a punishment. It is the gate doing its job, and it should be logged and
reported rather than negotiated.

---

## 22.4 Presentation rules **[M]**

| # | Rule |
|---|---|
| 1 | While `NOT_ASSESSMENT_READY`, exercises may run and diagnostic scores may be computed |
| 2 | **No assurance statement may be issued** |
| 3 | Every artifact produced in this state carries `TRAINING_OR_ENGINEERING_USE_ONLY` |
| 4 | A diagnostic score is **never** forwarded to an auditor, regulator, customer, or board as assurance evidence |
| 5 | **Removing the marking requires a state transition, not an editorial decision** |

Rule 5 is the one that gets tested in practice. The marking will look inconvenient on a slide
three weeks before an audit. That is precisely when it is doing the most work.

---

## 22.5 How this interacts with scoring

The readiness gate sits **above** the [§18 aggregation logic](17_capability_assessment.md) — it
is evaluated first, and it governs what the result may be *called*, not what it *is*:

```
1. readiness_gate      -> may this result be presented as assurance at all?
2. auto_fail check     -> did any team trigger an automatic failure?
3. evidence check      -> is evidence complete?
4. aggregation         -> weighted score -> readiness band
5. challenge review    -> triggered at 95-100%
```

A program can be `NOT_ASSESSMENT_READY` **and** produce a diagnostically useful 87%. Both facts
are true; only one of them may be reported outward.

---

## 22.6 What is left

The remaining work is **no longer primarily documentation**. It is proving that these function
**under failure conditions**:

| Property | Proven by |
|---|---|
| Identity separation | Attempting authorization as Red and being denied |
| Key custody | Rotation and recovery exercised, not just documented |
| Revocation | Tested end to end, including with the holder unavailable |
| Containment | Path-escape test passing on **every** supported platform |
| Canonical-source control | CI rejecting a duplicate package identity |
| Exercise Assurance | A named, COI-screened performer signing a result with the assessment key |

Once closure items 1–4 produce **independently verifiable** evidence, the program transitions to
`ASSESSMENT_READY` and there is a defensible basis for the first formal integrated assessment.

Until then: run the exercises, learn from them, and mark the outputs honestly.
