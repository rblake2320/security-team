"""Hard, kernel-enforced resource ceiling for subprocess trees.

Built in direct response to a real incident (2026-08-15): a test spawning
`claim_check.py` recursively produced 100+ live processes and tens of GB of RAM in
under 4 minutes, taking down the host. The team's cross-examination converged
independently (opus, sonnet, cybersecurity) on why a `psutil`-polling watchdog is not
the right primary defense: it has a sampling interval, and between two polls a
multiplicative spawn (this incident's exact shape) can burst past any threshold before
anything notices. A Windows Job Object's `ActiveProcessLimit` is enforced by the KERNEL
at `CreateProcess` time - there is no interval to miss a burst in.

PRECISION CAVEAT (sonnet, cross-examining the delivered version): what is directly,
precisely documented by Microsoft is that the SPECIFIC process whose creation would
push the job over `ActiveProcessLimit` is refused/terminated - not that the entire job
is torn down as an automatic consequence. The anti-fork-bomb property this module
relies on - that DESCENDANTS of the wrapped process inherit job membership and are
therefore subject to the same limit - is standard, well-established Windows behavior,
but has not yet been pinned to a citation as precise as the top-level explicit-
assignment case, and has not yet been confirmed by an adversarial test under verified-
calm system conditions (two independent memory-pressure reports disagreed on whether
conditions actually cleared - see git history). Treat the "no interval to miss a burst
in" claim as correct for the case tested (the offending new process refused outright);
treat "the whole tree is contained" as the design intent, not yet empirically closed.

The Windows path's process-creation dance (`CreateProcess` with `CREATE_SUSPENDED`,
`AssignProcessToJobObject`, then `ResumeThread`) is opus's design
(`PKA coordination/job_object_guard.py`), adopted here because it cleanly solves a
problem this file's own first draft got stuck on: `subprocess.Popen` does not expose a
way to retroactively open the main thread of an already-created process, so assigning
the job BEFORE the process can run anything requires the lower-level `CreateProcess`
API directly, which returns the thread handle as part of creation.

Two things opus's original delivered version did not yet have, added here after
cross-examining it:
  - A timeout. `WaitForSingleObject(hProcess, INFINITE)` meant a hang in the wrapped
    command hung the wrapper too - undermining the exact goal of bounding worst case.
  - Captured stdout/stderr, needed so `run_ci.py` can report gate failures with detail
    rather than just an exit code.

POSIX (the `ubuntu-latest` CI leg) has no Job Object equivalent without cgroups/root, so
it gets a process-group plus `RLIMIT_NPROC` set via `preexec_fn`. Documented weaker
guarantee, not hidden: `RLIMIT_NPROC` caps the REAL USER ID machine-wide, not a true
per-tree limit - acceptable on a dedicated, ephemeral CI runner where no unrelated
process shares that user, same platform-split pattern already used in this program (see
`exercise/filelock.py`).
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_PROCESSES = 25
DEFAULT_MAX_MEMORY_MB = 4096
DEFAULT_TIMEOUT_SECONDS = 1200


@dataclass
class GuardedResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def run_guarded(
    argv: list[str],
    *,
    cwd: str | None = None,
    env: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_processes: int = DEFAULT_MAX_PROCESSES,
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
) -> GuardedResult:
    """Run `argv` with a hard, kernel-enforced ceiling on the WHOLE process tree it
    spawns - not just the direct child. Always returns; never raises for a guarded
    failure (timeout, process-limit kill) - check the returned fields instead."""
    if sys.platform == "win32":
        return _run_guarded_windows(argv, cwd=cwd, env=env, timeout=timeout,
                                     max_processes=max_processes, max_memory_mb=max_memory_mb)
    return _run_guarded_posix(argv, cwd=cwd, env=env, timeout=timeout,
                               max_processes=max_processes)


# --------------------------------------------------------------------------- Windows

def _run_guarded_windows(argv, *, cwd, env, timeout, max_processes, max_memory_mb) -> GuardedResult:
    import tempfile
    import uuid

    import win32api
    import win32con
    import win32event
    import win32file
    import win32job
    import win32process
    import win32security

    job = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    info["BasicLimitInformation"]["LimitFlags"] = (
        win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        | win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
        | win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        | win32job.JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
    )
    info["BasicLimitInformation"]["ActiveProcessLimit"] = max_processes
    info["JobMemoryLimit"] = max_memory_mb * 1024 * 1024
    win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)

    # FILES, not anonymous pipes, for stdout/stderr capture.
    #
    # CONFIRMED LIVE (2026-08-17, not theorised): pipes deadlock here. Windows
    # inherits a pipe write-handle into every descendant a wrapped gate spawns, not
    # just the direct child - Python's own subprocess.close_fds=True default does
    # NOT protect fds 0/1/2, by design, so a gate that itself spawns pytest or
    # multiprocessing workers (both real, legitimate uses in this program) leaves a
    # copy of the write handle open in a grandchild. ReadFile on the read end then
    # blocks forever waiting for an EOF that never comes, because Windows only
    # signals it once EVERY handle to the write end is closed - not just the direct
    # child's. Reproduced on two independent gates (exercise/tests' multiprocessing
    # nonce-race test, claim_check.py's own pytest sub-spawn) with live process
    # inspection: parent + descendants, all near-zero CPU, all blocked.
    #
    # A file does not have this failure mode. The parent does not need the writer
    # to close anything - it opens its own independent handle to the same file and
    # reads whatever is there once WaitForSingleObject says the direct child is
    # done, share-flagged so a still-alive grandchild holding the file open cannot
    # block that read. This does not fix handle over-inheritance (a descendant can
    # still write to the file after the direct child exits, in the rare case one
    # outlives it) but it fixes the DEADLOCK, which is the property that matters
    # for a CI gate: this call must always return.
    tmp_dir = Path(tempfile.gettempdir())
    token = uuid.uuid4().hex
    out_path = tmp_dir / f"job_guard_out_{token}.log"
    err_path = tmp_dir / f"job_guard_err_{token}.log"

    sa = win32security.SECURITY_ATTRIBUTES()
    sa.bInheritHandle = True
    share = win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE
    out_write = win32file.CreateFile(
        str(out_path), win32con.GENERIC_WRITE, share, sa,
        win32con.CREATE_ALWAYS, win32con.FILE_ATTRIBUTE_NORMAL, None,
    )
    err_write = win32file.CreateFile(
        str(err_path), win32con.GENERIC_WRITE, share, sa,
        win32con.CREATE_ALWAYS, win32con.FILE_ATTRIBUTE_NORMAL, None,
    )

    startup = win32process.STARTUPINFO()
    startup.dwFlags |= win32process.STARTF_USESTDHANDLES
    startup.hStdOutput = out_write
    startup.hStdError = err_write
    startup.hStdInput = win32api.GetStdHandle(win32api.STD_INPUT_HANDLE)

    creationflags = win32process.CREATE_SUSPENDED | win32process.CREATE_NEW_PROCESS_GROUP
    # pywin32's CreateProcess wants the raw mapping for `newEnvironment` (it builds the
    # null-separated block internally) - passing a pre-built string here made it try
    # `.values()` on a str and fail on every call that supplied a non-None env, i.e.
    # every real run_ci.py gate. Only surfaced once this was actually wired in and run
    # end-to-end; the unit test didn't exercise this path (env=None default).
    try:
        hProcess, hThread, pid, _tid = win32process.CreateProcess(
            None, _quote_cmdline(argv), None, None, True,
            creationflags, env, cwd, startup,
        )
    except Exception as exc:
        with contextlib.suppress(Exception):
            win32api.CloseHandle(out_write)
            win32api.CloseHandle(err_write)
        return GuardedResult(96, "", f"job_guard: CreateProcess failed: {exc}", timed_out=False)
    finally:
        # The child has its own inherited copy; the parent's copy must still be
        # closed so the file isn't held open unnecessarily, but unlike the pipe
        # case this is cleanup hygiene, not correctness the return value depends on.
        with contextlib.suppress(Exception):
            win32api.CloseHandle(out_write)
        with contextlib.suppress(Exception):
            win32api.CloseHandle(err_write)

    try:
        try:
            win32job.AssignProcessToJobObject(job, hProcess)
        except Exception as exc:
            win32process.TerminateProcess(hProcess, 1)
            return GuardedResult(96, "", f"job_guard: AssignProcessToJobObject failed: {exc}",
                                 timed_out=False)

        win32process.ResumeThread(hThread)

        wait_ms = int(timeout * 1000) if timeout else win32event.INFINITE
        wait_result = win32event.WaitForSingleObject(hProcess, wait_ms)
        timed_out = wait_result == win32event.WAIT_TIMEOUT

        if timed_out:
            # TerminateJobObject kills EVERY process ever assigned to this job,
            # including all descendants - the whole-tree guarantee a direct
            # TerminateProcess on just hProcess would not provide.
            with contextlib.suppress(Exception):
                win32job.TerminateJobObject(job, 1)
            exit_code = -1
        else:
            exit_code = win32process.GetExitCodeProcess(hProcess)

        def _read_and_clean(path: Path) -> bytes:
            data = b""
            with contextlib.suppress(OSError):
                data = path.read_bytes()
            with contextlib.suppress(OSError):
                path.unlink()
            return data

        return GuardedResult(
            returncode=exit_code,
            stdout=_read_and_clean(out_path).decode("utf-8", errors="replace"),
            stderr=_read_and_clean(err_path).decode("utf-8", errors="replace"),
            timed_out=timed_out,
        )
    finally:
        with contextlib.suppress(Exception):
            win32job.TerminateJobObject(job, 1)
        for handle in (hThread, hProcess, job):
            with contextlib.suppress(Exception):
                win32api.CloseHandle(handle)
        # Belt and suspenders: _read_and_clean() already unlinks both files on the
        # success path, but any early return above (CreateProcess/AssignProcessToJob
        # failure) leaves them on disk with nothing to clean them up.
        for leftover in (out_path, err_path):
            with contextlib.suppress(OSError):
                leftover.unlink()


def _quote_cmdline(argv: list[str]) -> str:
    def q(a: str) -> str:
        return f'"{a}"' if (" " in a or "\t" in a) else a
    return " ".join(q(a) for a in argv)


# --------------------------------------------------------------------------- POSIX

def _run_guarded_posix(argv, *, cwd, env, timeout, max_processes) -> GuardedResult:
    import resource

    def _limit_nproc():
        # Runs in the CHILD after fork, before exec.
        with contextlib.suppress(Exception):
            _soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            resource.setrlimit(resource.RLIMIT_NPROC, (max_processes, hard))
        os.setsid()  # new session/process group; enables killpg on the whole tree

    proc = subprocess.Popen(
        argv, cwd=cwd, env=env, preexec_fn=_limit_nproc,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return GuardedResult(proc.returncode, stdout, stderr, timed_out=False)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            stdout, stderr = proc.communicate(timeout=5)
        return GuardedResult(-1, stdout or "", stderr or "", timed_out=True)
