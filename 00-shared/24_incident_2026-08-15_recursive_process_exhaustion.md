# Incident record — 2026-08-15 recursive process exhaustion

Not part of the numbered operating-model sequence (§1–§22) — appended as a durable
record of a real host-crashing incident, its root cause, and its fixes, so this
program's own history stays in the repository rather than only in ephemeral
coordination artifacts. Every fact below is traceable to a commit SHA on `main` or
was independently reproduced by more than one reviewer before being accepted.

## What happened

During adversarial testing of the assurance-claim gate, `00-shared/tools/claim_check.py`'s
evidence collector (`collect_node_ids()`) recursively re-invoked itself: it walks
`00-shared/tools` as one of the packages it collects evidence from, and that walk
included `test_gate_manifest.py`, which itself spawns `claim_check.py` as a subprocess.
Each spawned instance repeated the same walk. `00-shared/config/ci_gates.json` declares
four separate gate entries sharing `path: "00-shared/tools"`
(`repo-hygiene`, `ci-separation`, `gate-drift`, `commitment`), and the original collector
iterated gate *entries* rather than deduplicated *paths* — a branching factor of ~4 per
level, not a linear one. Live observation during the incident: 100+ `python.exe`
processes, most at 500–620MB RSS, growing over roughly four minutes before the host
became unresponsive and the process tree was killed by hand.

This was reachable through ordinary use, not only the adversarial test that triggered
it: `.github/workflows/engineering-integrity.yml` runs
`python -m unittest discover -s 00-shared/tools -p 'test_gate_manifest.py' -v` as a
standard CI step, which collects and executes the same recursive test. Confirmed live
via `gh run list` against this repository's own Actions history, not assumed from a
static read.

## Root cause, independently confirmed

Two reviewers traced the ~4x branching factor independently from source — one from
live process-count observation during the incident, one afterward from a cold read of
`00-shared/config/ci_gates.json` (exactly four `"path": "00-shared/tools"` entries) —
and reached the same number before comparing notes.

## Fixes (commit order)

| Commit | What |
|---|---|
| `d079f728` | Root cause: `CLAIM_CHECK_RECURSION_GUARD` env-var guard set on every subprocess `collect_node_ids()` spawns, checked as the collector's first statement; `unique_paths` dedup collapses the 4x `ci_gates.json` duplication to 1x. Bundled with R2-F7/F8/F9 evidence-collection hardening found in the same review pass (evidence node IDs are now resolved against real pytest/unittest collection instead of trusted as strings; an unresolvable package no longer silently masks every other claim). |
| `f6d360a8` | `purple-team/src/aegis_purple/scoring.py` had the identical defect pattern — readiness derived from an author-editable list instead of the underlying `gate_definitions` status (the fourth instance of this pattern found across the codebase; see also `d01126d1` below, pre-incident). |
| `e247e37d` | `run_ci.py`'s subprocess call had no `timeout=`, unlike sibling gate-runners — a hang risk found by the same static sweep that surfaced the recursion. |
| `de99b89e` | `00-shared/tools/job_guard.py` added — a kernel-enforced process-tree ceiling via a Windows Job Object (`ActiveProcessLimit`, `JobMemoryLimit`), with a documented weaker `RLIMIT_NPROC` fallback for the POSIX CI leg. The team's converged reasoning: a `psutil`-style polling watchdog has a real sampling-interval blind spot between polls; a kernel-enforced ceiling has none — the (N+1)th process creation past the limit is refused at `CreateProcess` time, not detected after the fact. |
| `01661fd7` | `exercise/filelock.py`'s `exclusive_lock` used `msvcrt.LK_LOCK`, which retries internally (Python's own `msvcrt` docs: up to 10 attempts) independent of the caller's requested `timeout` — a short-timeout caller could block far longer than requested. Switched to `LK_NBLCK` inside the existing Python-level poll loop so the requested timeout is actually the one enforced. Found and reproduced with a real separate-process lock-holder, not asserted. |
| `f2d1e038` | Corrected `job_guard.py`'s documentation to state its containment guarantee precisely — descendant containment relies on standard Windows job-inheritance and had not yet been empirically closed by an adversarial test at time of writing, distinct from the top-level explicit-assignment case which had. |

Related, already fixed *before* this incident and not caused by it, but the same
defect shape: `d01126d1` and `8c60da74` closed an earlier readiness-gate bypass
(`required_gates` list vs. `gate_definitions` ground truth) — `f6d360a8` above is the
fourth confirmed instance of that same "trusts a self-declared field instead of the
value next to it" pattern, across two unrelated files.

## Open at time of writing

- `job_guard.py` wiring into `run_ci.py` — in progress.
- `exercise/filelock.py`'s symlink-lock-path vector — could not be tested on the
  review host (`SeCreateSymbolicLinkPrivilege` not held by that account); not claimed
  as closed.
- Adversarial fork-bomb re-test of `job_guard.py`'s process-count ceiling — first
  attempt was inconclusive due to ambient host memory pressure unrelated to the guard
  itself; a clean re-run under confirmed-calm conditions is expected to close it.

## Process note

Found, root-caused, and fixed by three independently running Claude Code agents
(`claude-opus`, `claude-cybersecurity`, `claude-sonnet`) cross-examining each other's
claims against source and reproductions rather than accepting them — the explicit
instruction given was to disagree with evidence, not agree by default. A designated
keeper-of-record consolidated findings into this repository rather than leaving them
only in session-local coordination files.
