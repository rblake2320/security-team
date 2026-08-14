# §19 — Exercise Assurance Authority

← [Index](../README.md) · Related → [§18 Capability Assessment](17_capability_assessment.md) · [§3 Org & SoD](02_org_structure_and_raci.md) · [white-team](../white-team/CHARTER.md)

**Status:** governance decision, program owner, 2026-08-14.
**Constitutes:** a **role**, not an eighth colour team.

---

## 19.1 The problem it solves

White cannot hold the inject list, control the exercise, **and** grade itself. That violates
**SoD-4** (the scorer may not be a participant), and it makes the White scorecard's 90% threshold
self-reported.

The fix is not to take control away from White.

> **White still controls the exercise. Exercise Assurance assesses how White performed that
> control.**

That distinction is the whole design. Confuse the two and you get a second controller, ambiguous
authority during a live exercise, and a slower stop decision — which is worse than the problem.

---

## 19.2 Who performs it

Selection is driven by the assurance level the exercise requires:

| Assurance level | Performed by | When |
|---|---|---|
| **Internal** | **Internal Audit** | Internally assessed exercises — the default |
| **Higher assurance** | **External facilitator** | Exercises informing executive or board decisions; first-time program assessment; after any contested result |
| **Framework-mandated** | **3PAO · C3PAO · QSA** or the assessor the framework names | When the applicable framework requires external organizational independence ([§11 F-1](10_compliance_crosswalk.md)) |

**Not a standing team.** The role is constituted per exercise, or per assessment cycle, and
dissolves. It has no operational duties and no headcount of its own.

---

## 19.3 Permissions — exhaustive

Exercise Assurance may do these six things and **nothing else**:

| # | Permission | Note |
|---|---|---|
| **EA-1** | **Hold the sealed inject package** | White must not know which governance problems are coming (§18 A-2) |
| **EA-2** | **Observe White decisions** | Observe. Not advise, not participate, not concur |
| **EA-3** | **Validate timestamps and evidence** | Including the conflicting-timestamp inject |
| **EA-4** | **Compute the White score** | Against the rubric frozen before execution |
| **EA-5** | **Sign the final assessment result** | With the **assessment key** ([§20](19_aegis_trust_model.md)) |
| **EA-6** | **Report interference or conflicts of interest** | Direct line to the Executive Sponsor and the Audit Committee, bypassing everyone |

### Explicitly denied
- Controlling the exercise, or any part of it
- Approving or denying an RoE, a scope change, or a resumption
- **Calling or overriding a stop** — EA may *observe* that a stop was mishandled; it may not
  countermand White in flight. (EA retains the same right any human has to call a stop on
  **safety** grounds — that right belongs to everyone and is not an assurance power.)
- Directing any of the seven teams
- Altering execution evidence, the audit ledger, or any artifact
- Participating in the scenario in any way

**Rationale for the boundary:** an assurance function that can intervene is a participant, and a
participant cannot provide assurance. The moment EA can change the outcome, its signature on the
score means nothing.

---

## 19.4 The sealed inject package

```yaml
inject_package:
  package_id: "IP-2026-014"
  exercise_id: "EX-2026-014"
  sealed_by: "<Exercise Assurance>"
  sealed_at: "2026-09-14T09:00:00Z"
  seal_hash: "sha256:..."            # published to White BEFORE the exercise, contents withheld
  unseal_conditions:
    - "Exercise end"
    - "White Team termination of the exercise"
    - "Executive Sponsor direction"
  injects:
    - id: "INJ-01"
      trigger: "T+02:00 or first successful lateral movement, whichever is earlier"
      type: "scope_pressure"
      content: "System owner requests scope expansion mid-execution"
      assesses: ["A", "G"]           # White scorecard components
      expected_correct_response: "Deny, or route through documented amendment with re-signature"
      auto_fail_if: "Scope expanded without documented authorization"
    - id: "INJ-02"
      trigger: "T+03:30"
      type: "real_incident_ambiguity"
      content: "Exercise traffic resembles a genuine compromise"
      assesses: ["S", "G"]
      expected_correct_response: "Deconflict within SLA; where uncertain, treat as REAL"
      auto_fail_if: "Confident 'not exercise' given without certainty"
  safety_override: >
    Any inject may be withdrawn by Exercise Assurance if it would create genuine risk.
    A withdrawn inject is recorded, not silently dropped.
```

### The commitment: `aegis.inject-commitment.v2` **[M]**

> ⚠ **v1 is DEPRECATED and must not be used. It did not provide hiding.** Its `nonce` was
> published in the signed object — and was not in the digest preimage at all — so it contributed
> nothing to hiding *or* binding, while its field description asserted a property the
> construction never implemented. v1 was never used: the program has been
> `NOT_ASSESSMENT_READY` throughout.

A hash commitment needs **two** properties:

| Property | Meaning | Provided by |
|---|---|---|
| **Binding** | EA cannot substitute a different inject package after committing | The digest over the package |
| **Hiding** | White cannot enumerate likely packages and discover the injects before reveal | **Secret randomness withheld until reveal** |

```
c = H( domain ‖ canonical_package ‖ r )        r = fresh, high-entropy, WITHHELD
```

At reveal EA publishes the package **and** `r`; White recomputes `c`. Standard commit/reveal.

> **Randomness added to a hash defeats enumeration only when the attacker does not already know
> that randomness.** A published nonce gives uniqueness, not hiding. Inject packages are short
> and structurally predictable, so this is an exploitable gap in practice, not a theoretical one.

### Field disposition

| Field | Published at commitment | Purpose |
|---|---|---|
| `commitment_id` | **Yes** | Public uniqueness and correlation |
| `commitment_digest` | **Yes** | Binds the package **and** the secret opening value |
| `public_nonce` | Optional | Replay/correlation uniqueness **only** |
| `opening_salt` | **No** | Blocks enumeration of possible inject packages (`AEGIS-COMMIT-HIDING-001`) |
| `inject_package` | **No** | The withheld content |
| `opening_salt` + package | **At reveal** | Opens and verifies the commitment |

**Public object** — [schema](../white-team/config/inject_commitment.schema.json) ·
[template](../white-team/templates/inject_commitment.json):

```json
{
  "type": "aegis.inject-commitment.v2",
  "commitment_id": "IC-EX-2026-001-001",
  "exercise_id": "EX-2026-001",
  "commitment_algorithm": "SHA-384",
  "commitment_digest": "<SHA-384(domain || canonical_package || opening_salt)>",
  "canonicalization": "JCS",
  "package_schema": "aegis.inject-package.v1",
  "package_version": 1,
  "created_at": "<UTC timestamp>",
  "valid_from": "<UTC timestamp>",
  "reveal_deadline": "<UTC timestamp>",
  "exercise_assurance_key_id": "<key-id>",
  "previous_commitment": null,
  "signature": "<EA signature>"
}
```

**Secret opening material, retained by EA** —
[schema](../white-team/config/inject_opening.schema.json):

```json
{
  "commitment_id": "IC-EX-2026-001-001",
  "opening_salt": "<32 or 48 cryptographically random bytes>",
  "inject_package": {
    "type": "aegis.inject-package.v1",
    "exercise_id": "EX-2026-001",
    "injects": []
  }
}
```

### Exact preimage encoding **[M]**

Use an unambiguous **length-framed** encoding, never raw string concatenation — raw
concatenation admits boundary-shifting between adjacent fields.

```
preimage =
    length(domain)            || domain            ||
    length(canonical_package) || canonical_package ||
    length(opening_salt)      || opening_salt

commitment_digest = SHA-384(preimage)
```

`length()` is an **8-byte big-endian unsigned integer** giving the byte length of what follows.
`domain` is the ASCII string `aegis.inject-commitment.v2`. Canonicalization is **JCS (RFC 8785)**,
declared in the object so verification is not left to convention.

### Verification sequence — twelve steps, by White **[M]**

1. Validate the public commitment schema
2. Verify the EA signature over every public field except `signature`
3. Confirm `type`, `exercise_id`, key ID, algorithm, and validity window
4. Confirm the commitment was published **before exercise execution**
5. Confirm the opening uses the expected package schema
6. Canonicalize the revealed package using the declared algorithm
7. Reconstruct the **length-framed** preimage
8. Recompute and **constant-time compare** the digest
9. Validate inject identifiers, count, ordering rules, and timestamps
10. Validate the supersession chain
11. Confirm the `opening_salt` has not appeared in another commitment
12. **Preserve the commitment, opening, package, and verification result as evidence**

Any failure invalidates the inject package and is reported under **EA-6**.

### Operational consequences **[M]**

> ⚠ **Corrected 2026-08-14.** Earlier guidance here said "maintain a salt registry so
> verification step 11 is answerable." **That was wrong.** Opening salts preserve hiding only
> while secret, so a broadly accessible list of *unrevealed* salts is a high-value disclosure
> point — one whose compromise would destroy hiding for every open commitment at once. Use a
> controlled **opening-material vault** instead:
> [schema](../white-team/config/opening_material_vault.schema.json).

**The backup must protect two properties at once**, and this is the part that is easy to get half
right:

| Property | Failure mode if unprotected |
|---|---|
| **Confidentiality before reveal** | Hiding destroyed; the blind-inject design is void |
| **Availability at reveal** | Commitment permanently unopenable — **indistinguishable from refusing to reveal** |

> **Solving only one breaks the commitment process in a different direction.** My earlier
> "back it up" advice solved availability and ignored confidentiality.

| Rule | Detail |
|---|---|
| Uniqueness checked **inside the vault at creation** | White receives an *attestation that the check ran* — never the corpus |
| Disclosed salts move to a **historical opening register after reveal** | Openly checkable once secrecy no longer matters |
| **Never expose unrevealed salts** for global duplicate checking | This was the defect in the superseded guidance |
| Reuse detection is primarily **CSPRNG-health evidence** | With correct 256-bit+ salts, accidental collision is extraordinarily unlikely — a collision indicates a **broken generator**, not an ordinary duplicate |
| Backups encrypted under keys **distinct from all five program keys** | Otherwise the vault inherits the blast radius of the key model |
| **Dual control or threshold recovery** for backup access | Minimum two custodians |
| Recovery tested **before** the exercise, **without exposing the material** | Recover to a sealed check, not to a readable copy |
| Backup loss or failed recovery = **readiness regression** | Not a maintenance ticket |
| Destroy opening secrets only per retention policy | **Preserve the revealed package and verification evidence** (step 12) |

### Supersession **[M]**

> **A changed package requires a new signed commitment with an explicit supersession reason.
> Never overwrite the original.**

Both commitments remain published and chained; `package_version` increments and is never reused.
**A supersession created after exercise start is itself a finding**, reported under EA-6 — that
is the exact manoeuvre the commitment exists to make visible.

---

## 19.5 How it fits the org

```
        BOARD / AUDIT COMMITTEE
                 |
     +-----------+------------------------+
     |                                    |
 EXECUTIVE SPONSOR              EXERCISE ASSURANCE AUTHORITY
     |                          (Internal Audit | external | 3PAO/C3PAO/QSA)
     |                                    |
     |                          holds sealed injects; observes;
     |                          validates evidence; scores WHITE;
     |                          signs the result
     |                                    |
     |                                    v
     +------------------------->    WHITE TEAM  ---- controls the exercise ---->  7 teams
                                   (scores the other six)
```

**Scoring chain, complete:**

| Who is scored | Scored by |
|---|---|
| Purple, Yellow, Green, Orange, Blue, Red | **White** |
| **White** | **Exercise Assurance** |
| Exercise Assurance | Nobody — which is why its permissions are this narrow, and why EA-6 exists |

---

## 19.6 Conflict-of-interest rules **[M]**

| Rule | Detail |
|---|---|
| EA-COI-1 | The assurance performer must not have participated in the exercise being assessed, in any role |
| EA-COI-2 | Must not report to the CISO, to any team lead, or to the White Exercise Director |
| EA-COI-3 | Must not have designed the scenario or authored any test case |
| EA-COI-4 | Where Internal Audit performs the role, note that operational involvement can impair audit independence under IIA standards — **confirm scope with audit leadership before accepting**; observation and scoring are generally acceptable, exercise design is not |
| EA-COI-5 | An external facilitator engaged to assess must not also be engaged to remediate what it finds |
| EA-COI-6 | Rotate the performer at least every four exercises to prevent familiarity capture |

**EA-6 reporting is not discretionary.** If a participant attempts to influence the score, learn
the inject contents, or edit evidence after the fact, that goes to the Executive Sponsor and the
Audit Committee — regardless of seniority.

---

## 19.7 What EA produces

| Artifact | Contents | Signed with |
|---|---|---|
| **Assurance statement** | Whether the exercise was controlled as documented; whether evidence is complete and internally consistent; whether any interference occurred | **Assessment key** ([§20](19_aegis_trust_model.md)) |
| **White scorecard** | Component scores against the frozen rubric, with evidence references | Assessment key |
| **Evidence completeness determination** | Feeds the `INSUFFICIENT_EVIDENCE` program status ([§18](17_capability_assessment.md)) | Assessment key |
| **Inject performance record** | Per inject: fired at, White's response, expected response, verdict | Assessment key |
| **Interference report** | Only where applicable — direct to Executive Sponsor + Audit Committee | Assessment key |

**The assessment key is EA's alone.** It cannot sign authorizations, cannot seal execution
evidence, and cannot be used to alter anything — see the invariants in
[§20](19_aegis_trust_model.md).

---

## 19.8 Staffing and cost

| Profile | Performer | Effort per exercise |
|---|---|---|
| P1 | Internal Audit, or a contracted facilitator | ~4–8 hours |
| P2 | Internal Audit; external facilitator annually | ~8–16 hours |
| P3 | Internal Audit; the framework-named assessor for formal cycles | ~16–40 hours + framework assessment scope |

**This is the cheapest control in the entire model relative to what it protects.** Without it,
the single most important number in the program — how well the authorization and safety function
performed — is self-reported.
