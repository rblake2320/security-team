# Incident record — 2026-08-15 recursive process exhaustion

Not part of the numbered operating-model sequence (§1–§23) — appended as a durable
record of a real host-crashing incident, its root cause, and its fixes, so this
program's own history stays in the repository rather than only in ephemeral
coordination artifacts. Every fact below is traceable to a commit SHA on `main`, or
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
| `f6d360a8` | `purple-team/src/aegis_purple/scoring.py` had the identical defect pattern — readiness derived from an author-editable list instead of the underlying `gate_definitions` status. The fourth confirmed instance of "trusts a self-declared field instead of the value next to it," across two unrelated files — `d01126d1`/`8c60da74` closed an earlier instance of the same pattern before this incident, unrelated to it. |
| `e247e37d` | `run_ci.py`'s subprocess call had no `timeout=`, unlike sibling gate-runners — a hang risk found by the same static sweep that surfaced the recursion. |
| `de99b89e`, `f2d1e038`, PR [#2](https://github.com/rblake2320/security-team/pull/2) | `00-shared/tools/job_guard.py` — a kernel-enforced process-tree ceiling via a Windows Job Object (`ActiveProcessLimit`, `JobMemoryLimit`), with a documented weaker `RLIMIT_NPROC` fallback for the POSIX CI leg. Rejected a `psutil`-polling watchdog as the primary mechanism: polling has a sampling interval, and an exponential-shaped spawn can burst past any threshold in the gap between two polls; a kernel-enforced ceiling has none — the (N+1)th process creation past the limit is refused at `CreateProcess` time, not detected afterward. `f2d1e038` corrected the module's own documentation after a reviewer found the documentation overstated this property: the top-level explicit-assignment case is directly documented; that *descendants* of the wrapped process inherit job membership and are bound by the same limit is standard Windows behavior but had not been pinned to as precise a citation, nor closed by an adversarial test at time of writing. PR #2 fixed a real bug found while verifying it (pywin32's `CreateProcess` wants the raw environment mapping, not a pre-built block string — every call with a non-default `env` failed) and added an adversarial, self-bounded multiplicative-spawn test proving the cap holds; independently re-run and confirmed by a second reviewer before this record was written. |
| `01661fd7` | `exercise/filelock.py`'s `exclusive_lock` used `msvcrt.LK_LOCK`, which retries internally (Python's own `msvcrt` docs: up to 10 attempts) independent of the caller's requested `timeout` — a short-timeout caller could block far longer than requested. Switched to `LK_NBLCK` inside the existing Python-level poll loop so the requested timeout is actually the one enforced. Found and reproduced with a real separate-process lock-holder, not asserted; falsification-verified (reverting the fix reproduces the exact failure). |

## Open at time of writing

- **Wiring `job_guard.py` into `run_ci.py` is explicitly NOT done, and was actively
  reverted rather than shipped uncertain.** One full end-to-end run through every gate
  completed cleanly in ~65s; an immediately following second attempt, same command, no
  code changes, timed out at 300s with zero output — not even the first gate's own
  output — and no process-count growth was observed afterward (this was not a repeat of
  the original incident). Two independent reviewers examined this:
  - The nested-subprocess pipe-handle-inheritance hypothesis (`run_ci.py` → `job_guard`
    → `python -m unittest` → `claim_check.py`'s own further `pytest` subprocesses
    inheriting the guard's stdout/stderr write-handles several levels deep, so a
    distant descendant holding one open blocks `ReadFile` on EOF regardless of whether
    the directly-wrapped process has exited) is a real, documented Windows mechanism —
    confirmed against the actual PR #2 code, not assumed. But as coded, it is
    **insufficient by itself**: `job_guard.py`'s drain threads join with a 5-second
    bound (`t_out.join(timeout=5)`), so a pure pipe leak should let `run_guarded()`
    return within roughly ten seconds of the direct child exiting, not stall the full
    observed 300s.
  - A simpler, cheaper-to-eliminate hypothesis: `job_guard.py`'s own
    `DEFAULT_TIMEOUT_SECONDS` is 1200 (20 minutes). If the reverted wiring called
    `run_guarded()` without passing an explicit `timeout=` matched to whatever outer
    watchdog was bounding the test invocation at 300s, `WaitForSingleObject` would be
    correctly waiting up to 20 minutes when an *external* kill cut the whole tree off
    first — which would also cleanly explain zero output with no pipe pathology
    required (Python's stdout is fully buffered, not line-buffered, against a pipe; an
    abrupt external kill loses whatever hadn't flushed yet).

  Neither is confirmed. Two concrete, cheap next steps, in order: (1) check what
  `timeout=` value the reverted wiring actually passed against whatever outer bound was
  in effect — if those budgets didn't match, that is the whole explanation and the fix
  is a one-line correction, not a handle-lifecycle rewrite; (2) if budgets already
  matched, reproduce the hang and inspect live handles to the pipe kernel object across
  the whole process tree (e.g. Sysinternals `handle64.exe`) to confirm the inheritance
  theory directly rather than by plausibility. **The mechanism will not be wired into
  the shared CI path until this reproduces predictably enough to fix with confidence:**
  one clean run out of two is "usually works," not "works," and the bar for a safety
  mechanism is higher than that.
- `exercise/filelock.py`'s symlink-lock-path vector — could not be tested on the
  review host (`SeCreateSymbolicLinkPrivilege` not held by that account); not claimed
  as closed.
- Adversarial fork-bomb re-test of `job_guard.py`'s process-count ceiling under a
  full, ordinary CI-shaped invocation (as opposed to the isolated synthetic spawner PR
  #2 already verifies) — blocked on the wiring issue directly above.
- No registered assurance claim yet exists for "this program's own tooling cannot
  exhaust host resources." When written, its falsification test must carry its own
  hard iteration cap, independent of the mechanism under test, so a bug in the fix can
  never make the *test* itself recursively unbounded — the exact shape of the original
  incident.

## Process note

Found, root-caused, and fixed by three independently running Claude Code agents
(`claude-opus`, `claude-cybersecurity`, `claude-sonnet`) cross-examining each other's
claims against source and reproductions rather than accepting them — the explicit
instruction given was to disagree with evidence, not agree by default. Two of the
three independently wrote a version of this record without initially knowing the
other had; this is the merged result, not either original in isolation. A designated
keeper-of-record consolidated findings into this repository rather than leaving them
only in session-local coordination files.
