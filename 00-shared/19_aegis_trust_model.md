# §20 — Aegis Trust Model: Key Separation

← [Index](../README.md) · Related → [§19 Exercise Assurance](18_exercise_assurance.md) · [red-team](../red-team/CHARTER.md) · [§3 SoD](02_org_structure_and_raci.md)

**Status:** governance decision, program owner, 2026-08-14. **Target state.**
**Current implementation state: NOT YET MET — see §20.4.**

---

## 20.1 The principle

> Aegis is the critical control plane. Its key model must distinguish **authorization**,
> **execution**, and **assessment** rather than treating them as one signature domain.

A single signing key that both authorizes work and seals the evidence of that work collapses two
different claims into one. Whoever holds it can assert both *"this was permitted"* and *"this is
what happened"* — which means neither assertion is independently verifiable.

---

## 20.2 The five keys

| Key | Holder | Purpose |
|---|---|---|
| **Authorization key** | **White approval authority** | Signs the authorized scope, time window, techniques, identities, and stop conditions |
| **Execution key** | **Red execution service** | Signs what Red actually attempted, and the tool identity used |
| **Evidence key** | **Append-only evidence service** | Seals events, hashes, timestamps, and ledger sequence |
| **Assessment key** | **Exercise Assurance** ([§19](18_exercise_assurance.md)) | Signs scores and confirms evidence completeness |
| **Emergency-revocation key** | **Designated executive authority** | Revokes active authorization and triggers fail-closed termination |

Five holders, five distinct claims, no holder able to make another's claim.

---

## 20.3 Enforcement invariants **[M]**

```
No execution without a valid White authorization signature.
No execution outside the signed scope or time window.
Red may attest to what it executed but cannot authorize that execution.
Red cannot rewrite or independently seal the evidence ledger.
White cannot score its own performance.
The assessor cannot alter execution evidence.
```

### The two-object rule

> **A valid authorization receipt and an execution receipt are separate objects.**
> Red must be **capable** of producing a signed execution record, and **incapable** of
> manufacturing the White authorization that makes the execution permissible.

| Object | Signed by | Asserts | Verifiable by |
|---|---|---|---|
| **Authorization receipt** | Authorization key (White) | *"This scope, window, and technique set were permitted"* | Anyone holding the White trust key |
| **Execution receipt** | Execution key (Red) | *"This is what I attempted, with this tool identity"* | Anyone holding the Red trust key |
| **Sealed ledger** | Evidence key (evidence service) | *"This sequence of events is complete and unaltered"* | Anyone holding the evidence trust key |
| **Assessment result** | Assessment key (EA) | *"These are the scores, and the evidence was complete"* | Anyone holding the EA trust key |

An investigator can then ask four independent questions and get four independently signed
answers. Under a single-key model, all four collapse into one party's word.

### Emergency revocation
| Property | Requirement |
|---|---|
| Effect | Revokes the active authorization; Aegis **fails closed** — running checks halt at their next safety boundary and no new execution starts |
| Holder | Designated executive authority — **not** White, **not** Red |
| Why separate from White | The revocation path must survive White being unavailable, compromised, or itself the problem |
| Relationship to `.aegis/STOP` | Complementary. `STOP` is a local, immediate, anyone-can-use halt. Revocation is authoritative and cannot be undone by removing a file. |
| Testing | **Exercise revocation at least annually**, as part of closure item 2 ([§21](20_closure_plan.md)) |

---

## 20.4 Current implementation state — key-purpose split complete **[VERIFIED]**

Aegis v0.2.0 has separate authorization and evidence signature domains, purpose-bound key
metadata, and negative tests rejecting reuse in either direction:

```
authorize      --signing-key            <- authorization-v1 key
seal-ledger    --evidence-signing-key   <- evidence-seal-v1 key
verify-ledger  --evidence-trust-key     <- evidence-seal-v1 trust key
```

| Target key | Present in v0.2.0? | Consequence today |
|---|---|---|
| Authorization key | **Yes** | Works as designed — Red cannot authorize |
| Execution key | **No** | Red cannot independently attest to what it attempted; the ledger is the only record, and it is sealed by the authorization holder |
| Evidence key | **Yes — separate purpose and domain** | Supported APIs reject authorization-key use for evidence sealing and evidence-key use for authorization |
| Assessment key | **No** | EA cannot cryptographically sign a score |
| Emergency-revocation key | **No** | Revocation is procedural (expiry, `.aegis/STOP`), not cryptographic |

The remaining key risk is deployment custody, not signature-domain design. Host administrators
with raw access can bypass application metadata, so distinct non-exportable stores, IAM denial,
rotation, recovery, revocation, and immutable use logs remain readiness requirements.

---

## 20.5 Migration path

Ordered so each step is independently useful and none requires a rewrite.

| # | Step | Effort | Yields |
|---|---|---|---|
| **1 — COMPLETE** | **Split the evidence key from the authorization key.** Separate domains, purpose metadata, CLI arguments, and bidirectional rejection tests | Complete 2026-08-14 | Closes application-level cross-purpose reuse |
| **2** | **Custody**: authorization key into a White-controlled HSM or secret manager; evidence key held by the evidence service; **IAM policy denying Red access to both** | Process + IAM | Closure item 2 ([§21](20_closure_plan.md)) — makes the control real rather than documented |
| **3** | **Execution receipt**: Red signs a record of attempted actions with an execution key; the receipt references the authorization receipt by fingerprint | Moderate — new object + schema | Red can prove what it did without being able to prove it was allowed |
| **4** | **Assessment key** for Exercise Assurance; EA signs scores and the completeness determination | Small | §19 signatures become verifiable |
| **5** | **Emergency revocation**: a revocation object checked at every safety boundary; presence of a valid revocation fails closed | Moderate | Authoritative stop that survives White being unavailable |
| **6** | **Rotation and recovery** documented and **tested** for all five keys | Process | A key model nobody can recover from is a single point of failure wearing a security label |

Step 1 is complete. Do not treat it as production independence until step 2 custody evidence is
verified through the signed dual-authority gate attestation.

---

## 20.5a Key status at signing time — expiration is not compromise **[M]**

Evaluating key status **as at `created_at`** avoids routine rotation incorrectly
retroactively invalidating legitimate signatures — a public verification key remains useful for
verifying previously generated signatures after the private key has expired. But **expiration,
administrative revocation, and compromise are different events and must not share one rule.**

| Condition | Disposition |
|---|---|
| **Routine expiration or rotation** after `created_at` | **Do not invalidate** an otherwise valid commitment |
| **Revocation for administrative reasons**, effective after `created_at` | **Preserve validity** unless policy explicitly says otherwise |
| **Known compromise beginning after `created_at`** | **Preserve validity** if trusted timestamp and evidence establish earlier signing |
| **Known or potentially *earlier* compromise** | `SIGNATURE_VALID_BUT_ASSURANCE_DISPUTED` → **manual assurance review required** |
| **Unknown compromise onset** | **Do not automatically accept or reject.** Escalate on the evidence below |

### Why `created_at` alone is not sufficient

**A self-declared `created_at` is not evidence when the signing key itself may have been
compromised** — whoever holds a compromised key can assert any timestamp they like. Temporal
claims need an *independent* anchor:

| Independent temporal evidence | Note |
|---|---|
| **Prior publication to White** | Already required — verification step 4 confirms the commitment preceded execution. This is the cheapest anchor you have and it exists already |
| **Append-only transparency record** | Third-party-observable ordering |
| **Trusted timestamp** | An established key-management consideration for signed data |
| HSM logs, key-use records | Supporting, not sufficient alone |
| Revocation reason | Determines which row of the table applies |

**`SIGNATURE_VALID_BUT_ASSURANCE_DISPUTED` is a real terminal state.** It is not a soft pass: the
signature verifies, and the assurance it was meant to convey does not. Resolving it is a human
judgement recorded under EA-6 — never an automatic acceptance because the maths checked out.

**Applies to all five keys**, not only the assessment key. The same reasoning governs a disputed
authorization receipt or a disputed ledger seal.

---

## 20.6 Key custody requirements **[M]**

| Requirement | Detail |
|---|---|
| Storage | HSM or a managed secret manager. **Never on an operator workstation.** |
| Access control | IAM policy explicitly denying Red identities access to the authorization and evidence keys — **policy AND IAM, not policy alone** |
| Passwords | From a secret manager at signing time; cleared from the environment afterwards |
| Rotation | Documented schedule; immediate rotation on any suspected exposure |
| Recovery | Documented, and **tested** — including the case where the holder is unavailable |
| Revocation test | Exercised at least annually |
| Audit | Every use of the authorization, evidence, and revocation keys logged to a store none of their holders can alter |
| **Detection** | A signing key found on an operator machine **halts the program**, triggers rotation, and is investigated by White — this is already a Red scorecard automatic-failure condition |

---

## 20.7 What this changes elsewhere

| Document | Change |
|---|---|
| [red-team/CHARTER.md](../red-team/CHARTER.md) | "Signing key" is now specifically the **authorization key**; Red will hold an execution key of its own |
| [§3 SoD](02_org_structure_and_raci.md) | SoD-2's compensating control is "cryptographic — *partially* implemented"; full implementation requires step 1 |
| [§19 EA](18_exercise_assurance.md) | The assessment key is EA's, and is one of the five |
| [§21 Closure](20_closure_plan.md) | Steps 1 and 2 are closure item 2 (R-10) |
| [red-team/ARTIFACTS.md](../red-team/ARTIFACTS.md) | The note comparing Aegis's anchor to Blue's is now qualified — Aegis's anchor is stronger *in design*, and equal in practice until the evidence key is split |
