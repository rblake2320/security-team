"""Cross-platform exclusive file lock and atomic write.

AUD-02 / AUD-08. The nonce ledger used an unlocked read-modify-write and a shared
`.tmp` sibling filename. Under a barrier-synchronised 6-process test this failed
12/12 rounds, with THREE processes each consuming the same nonce successfully -
replay protection did not merely report badly, it did not hold at all.

Two defects, one fix:
  * no mutual exclusion around read-modify-write, so several readers saw the same
    "nonce absent" state and all wrote
  * a predictable sibling temp path, so concurrent writers collided (PermissionError
    on Windows) instead of each writing their own file

`exclusive_lock` serialises the whole critical section. `atomic_write` gives every
writer a unique, securely created temp file, fsyncs it, and replaces atomically.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

if os.name == "nt":
    import msvcrt

    def _lock(handle) -> None:
        # SONNET-R2-F1 (external review, 2026-08-15, reproduced): LK_LOCK is
        # BLOCKING and retries INTERNALLY, inside the C runtime, up to ~10 times
        # before raising - a window invisible to and unbounded by the caller's own
        # `timeout`/deadline loop below. Reproduced with a real separate process
        # holding the lock and a caller requesting timeout=1.0: the call returned
        # success at ~3s (when the holder released), no TimeoutError, no exception
        # at all - the Python-level deadline check never got a chance to fire
        # because the single _lock() call it was waiting on hadn't returned yet.
        #
        # LK_NBLCK is genuinely non-blocking: it raises immediately if the byte is
        # locked, with no internal retry. That makes the Python-level poll-and-sleep
        # loop below the ONLY thing governing wait time, which is what the
        # `timeout` parameter's contract requires.
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock(handle) -> None:
        # SONNET-R2-F1 follow-up (CI-caught, 2026-08-15): the Windows branch above was
        # fixed for exactly this defect, but this branch was never touched, so the same
        # bug survived here - and worse, since flock(LOCK_EX) has no internal retry limit
        # at all: it blocks INDEFINITELY, not just for an internal ~10-attempt window. A
        # single call can absorb the caller's entire `timeout`, and then some, with the
        # Python-level deadline loop below never getting a chance to run.
        #
        # LOCK_NB makes flock() genuinely non-blocking: it raises immediately (an OSError,
        # already handled by the existing retry loop's `except OSError`) if the lock is
        # held, making that Python-level poll-and-sleep loop the only thing governing wait
        # time - matching the Windows branch and what `timeout`'s contract requires.
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def exclusive_lock(target: Path, timeout: float = 30.0) -> Iterator[None]:
    """Hold an exclusive lock covering a whole read-modify-write on `target`.

    The lock is taken on a sibling `.lock` file, never on the target itself, so the
    target can be atomically replaced while the lock is held.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = timeout
    handle = open(lock_path, "a+b")
    try:
        handle.seek(0)
        while True:
            try:
                _lock(handle)
                break
            except OSError:
                # msvcrt raises rather than blocking indefinitely; retry to the deadline.
                deadline -= 0.05
                if deadline <= 0:
                    raise TimeoutError(f"timed out acquiring lock on {lock_path}") from None
                import time
                time.sleep(0.05)
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                _unlock(handle)
    finally:
        handle.close()


def atomic_write(target: Path, data: str, *, mode: int = 0o600) -> None:
    """Write `data` to `target` atomically, via a unique temp file in the same dir.

    Same directory so `os.replace` stays atomic. Unique name so concurrent writers
    never collide. fsync before replace so a crash cannot leave a truncated file.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        with contextlib.suppress(OSError, NotImplementedError):
            os.chmod(temp_name, mode)
        os.replace(temp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


def atomic_write_bytes(target: Path, data: bytes, *, mode: int = 0o600) -> None:
    """Byte-oriented `atomic_write`, for canonical evidence written as exact bytes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        with contextlib.suppress(OSError, NotImplementedError):
            os.chmod(temp_name, mode)
        os.replace(temp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise
