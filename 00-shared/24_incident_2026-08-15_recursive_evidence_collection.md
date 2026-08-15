# §25 — Incident: recursive evidence collection (2026-08-15)

← [Index](../README.md) · Related → [§23 Assurance Claims](22_assurance_claims.md) · [§22 Readiness Gate](21_readiness_gate.md) · [§24 Completion Register](23_completion_register.md)

**Status:** closed for the specific defect; one precision item and one deferred
verification remain open (§6). This document is the permanent record — it does not
depend on any ephemeral coordination artifact surviving.

---

## 1 · What happened

A regression test added during a review session to satisfy an external finding
(evidence-collection gate did not verify the artifacts it certifies) itself spawned
`00-shared/tools/claim_check.py` as a subprocess. `claim_check.py`'s own
evidence-collection step (`collect_node_ids()`) walks the `00-shared/tools` package to
gather test evidence — which *is* the file containing that test. The test spawned the
tool; the tool's own evidence pass re-collected the test; the test spawned the tool
again. Unbounded recursive process creation, amplified roughly 4x by an unrelated
duplicate-path entry in `00-shared/config/ci_gates.json` (four gate entries shared one
`path` value, so the same directory was walked four times per recursion level).

**Measured, not estimated:** 100+ live `python.exe` processes, most at 500-620MB RSS,
observed directly via two `tasklist` snapshots roughly a minute apart before the tree
was killed by hand. This took down the host machine.

**Reachability:** confirmed via the actual GitHub Actions run history and a byte-for-byte
read of `.github/workflows/engineering-integrity.yml` — this is triggered by completely
ordinary execution of the program's own local/CI test runner, not only by the specific
test-development session that first exposed it.

**Permanent gap in the record:** the defective test was introduced and fixed entirely
within one uncommitted working-tree session — it exists in no commit. The original
failure is therefore not independently reproducible by anyone after the fact. This is
the direct reason §5 below is a standing rule, not a suggestion.

## 2 · Root cause

Two independent, structural defects, not one:

1. **No recursion guard.** `collect_node_ids()` had no mechanism to detect that it was
   already running inside its own evidence-collection pass before spawning another
   instance of the same tool.
2. **Duplicate path amplification.** Four `ci_gates.json` entries shared one directory
   path; the collector iterated gate *entries* rather than unique paths, multiplying
   every recursion level by roughly four.

## 3 · Fix — commits, in order, each independently verifiable

All in `github.com/rblake2320/security-team`, `main`:

| Commit | What it closes |
|---|---|
| `d079f728` | Recursion guard (environment-variable check, checked first-thing in the test, plus an independent second check inside the collector itself), path deduplication, sandbox execution against a throwaway copy with cleanup made unconditional via `try`/`finally`, and a path-comparison hardening found while fixing an external reviewer's finding on the same mechanism. |
| `f6d360a8` | An independent instance of the readiness-derivation defect this incident is adjacent to — `purple-team`'s own scoring path trusted an author-editable gate list rather than the authoritative gate-definition record; same class of bug, different module, found by an external review pass that had no prior context on the recursion incident. |
| `e247e37d` | Missing subprocess timeout in the local CI runner (found by a full-repo static sweep run in response to this incident). |
| `de99b89e`, `f2d1e038` | `00-shared/tools/job_guard.py` — a kernel-enforced process-tree ceiling (Windows Job Object; POSIX process-group + `RLIMIT_NPROC`), built so a *future* bug of this shape is contained by the operating system rather than by code review catching every possible recursive call site. Not yet wired into the CI runner — see §6. |
| `01661fd7` | An unrelated but adjacent defect found while attacking the locking primitive this fix depends on: `exercise/filelock.py`'s `timeout` parameter was silently unenforceable past roughly ten seconds because the underlying platform lock call retries internally in a way invisible to the caller's own deadline loop. Reproduced with a real second process holding the lock before the fix was written; falsification-verified (reverting the fix reproduces the exact failure) after. |

Every fix listed above was independently reproduced before being accepted — a
description or a confident claim was not treated as evidence anywhere in this list.

## 4 · Why a polling watchdog was rejected as the primary mitigation

The natural first proposal — a background thread polling live process count and
killing the tree past a threshold — was examined and rejected as the *primary* layer,
for a specific, checkable reason: a polling watchdog has a sampling interval, and an
exponential-shaped spawn can burst past any threshold in the gap between two polls. A
Windows Job Object's `ActiveProcessLimit` is applied by the kernel at process-creation
time - the offending process creation is refused outright rather than detected
afterward - so there is no interval in which a burst is invisible. `job_guard.py`
therefore uses the kernel primitive as the containment mechanism, with observability
left to whatever the operator already uses for process monitoring.

## 5 · Standing rule this incident produced

**Commit fixes atomically, one finding per commit, as they land — not as one bundled
diff at the end of a session.** The immediate, concrete cost of not doing this is
recorded in §1: the actual incident this document describes cannot be independently
bisected by anyone, including the person who caused it, because it lived only in an
uncommitted working tree. Every fix in §3 is a separate commit for this reason.

## 6 · Open items — not closed by omission

- **`job_guard.py`'s whole-tree containment claim is stated as design intent, not yet
  fully closed by an adversarial test.** What is directly documented is that the
  specific process whose creation would exceed the job's process limit is refused.
  That descendants of the wrapped process inherit job membership and are therefore
  bound by the same limit is standard, well-established Windows behavior, but had not
  been pinned to as precise a citation as the top-level case, nor independently
  confirmed by a bounded adversarial spawn test at the time of writing. Two
  independent system-load checks during this incident's investigation disagreed on
  whether conditions had cleared enough to run that test safely, so it was
  deliberately deferred rather than forced.
- **`job_guard.py` is not yet wired into `00-shared/tools/run_ci.py`.** The primitive
  is committed and reviewed; integrating it into the actual gate runner is a
  separate, separately-verifiable step.
- **No registered assurance claim yet exists for "this program's own tooling cannot
  exhaust host resources."** When one is written, its falsification test must carry
  its own hard iteration cap, independent of the mechanism under test — a bug in the
  fix must never be able to make the *test* recursively unbounded, which is exactly
  the shape of the original incident.
- A symlink-based attack on `exercise/filelock.py`'s lock path was identified as a
  theoretically real vector during this review but could not be tested in the
  environment available at the time (the test account lacked the privilege required
  to create a symlink on Windows). Not assumed safe by omission.
