# Operating Guide

Design index: [`README.md`](README.md) · Completion state: [`00-shared/23`](00-shared/23_completion_register.md)

**This file is for the person who has to run it**, not the person reading the design.

---

## Program state

```
PREREQUISITES_PENDING  ->  NOT_ASSESSMENT_READY
```

Exercises may run. Diagnostic scores may be computed. **No assurance statement may be
issued**, and every artifact carries `TRAINING_OR_ENGINEERING_USE_ONLY`. Two readiness
gates are pending and both need an external authority — see
[§24 A-section](00-shared/23_completion_register.md).

---

## First five minutes

```bash
cd "PKA testing/Purple team"

python 00-shared/tools/run_ci.py           # all 10 engineering gates
python 00-shared/tools/run_ci.py --assurance   # MUST fail (exit 1) - that is correct
python 00-shared/tools/install_hooks.py --force  # chain the pre-commit gate
```

If `--assurance` **passes**, something is wrong: readiness gates are pending, so the
assurance path must fail closed.

---

## Running the exercise rehearsal

```bash
cd exercise
python preflight.py --issue      # verify + issue a short-lived clearance
python run_rehearsal.py          # refuses without that clearance
python run_rehearsal.py          # REFUSED: nonce replay
```

| Behaviour | Expected |
|---|---|
| `run_rehearsal.py` invoked directly | `REFUSED [NO-CLEARANCE]`, exit 1 |
| Clearance reused | `REFUSED [CLEARANCE-REPLAY]`, exit 1 |
| `preflight.py --mode FORMAL_INTEGRATED_ASSESSMENT` | `REFUSED`, exit 1 — production trust store is empty |
| Any input changed after clearance | `REFUSED [CLEARANCE-MANIFEST]` |

**These refusals are the product.** A run that succeeds proves less than a run that
correctly refuses.

---

## Where things live

| Need | Path |
|---|---|
| Gate list (single source of truth) | `00-shared/config/ci_gates.json` |
| Local CI | `00-shared/tools/run_ci.py` |
| GitHub CI | `<repo-root>/.github/workflows/purple-team-integrity.yml` |
| Claim registry | `00-shared/config/assurance_claims.json` |
| Readiness gates | `00-shared/config/assessment_readiness.json` |
| Trust stores | `exercise/config/trust/production/` · `exercise/tests/fixtures/trust/` |
| What remains | `00-shared/23_completion_register.md` |

**The GitHub workflow lives at the repository root, not in this directory.** Actions
reads only `<repo-root>/.github/workflows/`; a workflow nested here is inert. Guarded
by `test_repo_hygiene.py`.

---

## Adding a gate

1. Add it to `00-shared/config/ci_gates.json`
2. Add the matching step to the root workflow
3. Run `run_ci.py`

Step 2 is not optional — `test_gate_manifest.py` fails if the workflow does not cover
the manifest. That guard exists because two hand-maintained gate lists always diverge.

---

## Making a claim

Never write that something is enforced, guaranteed, prevented, or satisfied without a
registered claim. `claim_check.py` rejects the language (R1) and rejects a claim with
no falsification test (R3).

```bash
# 1. write the mechanism
# 2. write a test that tries to BREAK it
# 3. register in 00-shared/config/assurance_claims.json
python 00-shared/tools/claim_check.py --allow-not-ready
```

Three defects in this program came from asserting a property with no traced mechanism.
The gate exists to catch the fourth.

---

## Secrets

| Rule | Enforcement |
|---|---|
| Fixture private keys never enter git | `.gitignore` + `test_repo_hygiene.py` + pre-commit block |
| Commitment opening material stays secret until reveal | `.gitignore`, `opening_material_vault.schema.json` |
| Nonce ledger is machine-local | gitignored; replay protection is **per host** |
| Production trust store holds public keys only | Empty today; `test_formal_mode_production_store_is_empty` |

**No production private key exists in this repository, and none should.**

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: aegis_purple` / `blue_team` / `aegis_rt` | Set `PYTHONPATH=<team>/src`. `run_ci.py` does this for you |
| `REFUSED [CLEARANCE-LEDGER-CORRUPT]` | Nonce ledger unreadable. **Fails closed by design** — do not delete it to "fix" it; investigate |
| `REFUSED [SB-MISSING-ATTESTATION]` | No signed environment attestation for this exercise |
| Pre-commit blocks on secret-shaped files | Working as intended. Unstage them |
| `--assurance` passes | **Investigate immediately.** It must fail while gates are pending |
