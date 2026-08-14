# §23 — The Assurance Claim Gate

← [Index](../README.md) · Registry → [`config/assurance_claims.json`](config/assurance_claims.json) · Tool → [`tools/claim_check.py`](tools/claim_check.py) · Tests → [`tools/test_commitment.py`](tools/test_commitment.py)

**Authority:** program owner decision, 2026-08-14.
**This document is the shortest file in the set on purpose.** The control is the code, not the
prose. A prose document arguing that prose claims are insufficient would refute itself.

---

## 23.1 The rule

> **No security property is credited because it appears plausible in prose. It is credited only
> when a scoped claim identifies a mechanism, states its assumptions, survives falsification
> attempts, and produces reviewable evidence.**

This exists because three defects in this program shared one root cause, and were initially
treated as unrelated drafting errors:

| Defect | What was asserted | What was missing |
|---|---|---|
| **F-1** | "Red closes the independence gap" | Four different independence requirements were collapsed into one |
| **SA-11(5)** | "unqualified" read as "satisfied" | No independence requirement ≠ requirement met |
| **Commitment v1** | "the nonce was claimed to block brute-forcing" | The nonce was **not in the preimage**. No mechanism existed at all |

All three were confident statements about security properties with no traced path from claim to
mechanism to evidence. Correcting them individually would have left the generator intact.

## 23.2 The invariant

```
CLAIM  !=  CONTROL  !=  MECHANISM  !=  EVIDENCE

A control    states the requirement.
A claim      states the property believed to hold.
A mechanism  attempts to create that property.
Evidence     supports or falsifies the claim.
An assessment determines whether the evidence is sufficient.
```

Conflating any two of these produces the failure above. The most common conflation is
**claim ↔ mechanism**: writing the property you intended next to the code you wrote, and
treating adjacency as implementation.

## 23.3 Required fields

Every normative claim registers: exact property · scope and environment · mechanism ·
assumptions · evidence · **negative tests attempting to falsify it** · owner · independent
reviewer where required · freshness and regression triggers · residual limitations.

Schema and current registry: [`config/assurance_claims.json`](config/assurance_claims.json).

## 23.4 Lifecycle

```
PROPOSED -> MECHANISM_IDENTIFIED -> TESTABLE -> EVIDENCED
         -> INDEPENDENTLY_REVIEWED -> OPERATIONAL

any failed dependency -> DISPUTED or REGRESSED
```

No state may be skipped. `OPERATIONAL` additionally requires every
[readiness gate](config/assessment_readiness.json) to be true.

## 23.5 CI enforcement

```bash
python 00-shared/tools/claim_check.py          # exit 0 pass / 1 violation / 2 not-ready
```

| Rule | Rejects |
|---|---|
| **R1** | Assertive assurance vocabulary without a `claim_id` reference |
| **R2** | A claim with no named mechanism |
| **R3** | A claim whose mechanism has no **positive and negative** tests |
| **R4** | A claim whose evidence is **documentation only** |
| **R5** | A claim referencing **skipped or stale** tests |
| **R6** | A claim marked `OPERATIONAL` while a readiness gate is false |
| **R7** | A mechanism changed without a claim-version increment and revalidation |

Plus: control mappings without **per-system** applicability determinations (see
[§11.14](10_compliance_crosswalk.md)).

**R1 is intentionally over-inclusive.** Each hit is a *candidate requiring triage*, not a
confirmed defect. Triage has two outcomes: register a claim, or reword. Both are improvements.

## 23.6 Current state — run 2026-08-14

| | |
|---|---|
| Readiness | **`NOT_ASSESSMENT_READY`** — two of four gates VERIFIED; two require external authorities |
| Claims registered | **15** |
| `EVIDENCED` | **12** — including split evidence keys and Windows/POSIX containment |
| `TESTABLE` | 0 |
| `MECHANISM_IDENTIFIED` | 3 — Red-cannot-authorize, Blue audit anchor, Red independence |
| `DISPUTED` | 0 |
| `REGRESSED` | 0 |
| R1 lint | **0 unsupported claim candidates**; the initial 26 were triaged by claim reference or non-assertive wording |

**Twelve of fifteen claims are evidenced locally.** The remaining three depend on organizational
independence, production custody, or external anchoring. Two early
findings surfaced only because the registry forced the question:

1. **`AEGIS-LEDGER-TAMPER-001` was half-evidenced and is now closed locally.** Aegis and
   Sentinel Blue both have falsification tests for mutation and interior deletion; Sentinel Blue
   also tests tail deletion against its stored head/count. Whole-store rollback remains outside
   the local chain boundary and requires external anchoring.
2. **`AEGIS-SOD-AUTHZ-001` still has no independent custody evidence.** "Red can execute but cannot authorize" is
   the model's strongest control, and **nobody has attempted to authorize as Red and been
   denied.** The mechanism is in the code; the demonstration does not exist.

Both were invisible in prose review across multiple passes.
