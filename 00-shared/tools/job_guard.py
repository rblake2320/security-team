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
    import win32api
    import win32con
    import win32event
    import win32job
    import win32pipe
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

    # Inheritable pipes so the child's stdout/stderr can be captured, mirroring
    # subprocess.PIPE semantics - CreateProcess does not accept Python file objects
    # directly, only OS handles.
    sa = win32security.SECURITY_ATTRIBUTES()
    sa.bInheritHandle = True
    out_read, out_write = win32pipe.CreatePipe(sa, 0)
    err_read, err_write = win32pipe.CreatePipe(sa, 0)
    win32api.SetHandleInformation(out_read, win32con.HANDLE_FLAG_INHERIT, 0)
    win32api.SetHandleInformation(err_read, win32con.HANDLE_FLAG_INHERIT, 0)

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
        return GuardedResult(96, "", f"job_guard: CreateProcess failed: {exc}", timed_out=False)
    finally:
        # The write ends belong to the child now; the parent must close its copies or
        # ReadFile on the read end will block forever waiting for a write end that will
        # never close.
        win32api.CloseHandle(out_write)
        win32api.CloseHandle(err_write)

    try:
        try:
            win32job.AssignProcessToJobObject(job, hProcess)
        except Exception as exc:
            win32process.TerminateProcess(hProcess, 1)
            return GuardedResult(96, "", f"job_guard: AssignProcessToJobObject failed: {exc}",
                                 timed_out=False)

        win32process.ResumeThread(hThread)

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        # Read each pipe to EOF in its own thread so a child that writes heavily to
        # stderr while stdout is quiet (or vice versa) cannot deadlock the parent on a
        # full pipe buffer.
        import threading

        def _drain(handle, sink):
            with contextlib.suppress(Exception):
                while True:
                    _err, chunk = win32file_read(handle)
                    if not chunk:
                        break
                    sink.append(chunk)

        t_out = threading.Thread(target=_drain, args=(out_read, stdout_chunks), daemon=True)
        t_err = threading.Thread(target=_drain, args=(err_read, stderr_chunks), daemon=True)
        t_out.start()
        t_err.start()

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

        t_out.join(timeout=5)
        t_err.join(timeout=5)

        return GuardedResult(
            returncode=exit_code,
            stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
            stderr=b"".join(stderr_chunks).decode("utf-8", errors="replace"),
            timed_out=timed_out,
        )
    finally:
        with contextlib.suppress(Exception):
            win32job.TerminateJobObject(job, 1)
        for handle in (hThread, hProcess, job, out_read, err_read):
            with contextlib.suppress(Exception):
                win32api.CloseHandle(handle)


def win32file_read(handle, size=65536):
    import pywintypes
    import win32file

    try:
        return win32file.ReadFile(handle, size)
    except pywintypes.error as exc:
        # ERROR_BROKEN_PIPE: the write end closed (child exited) - normal EOF, not a
        # real failure.
        if exc.winerror == 109:
            return (0, b"")
        raise


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
