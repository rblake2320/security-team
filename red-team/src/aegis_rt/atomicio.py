"""Atomic, non-predictable file writes for engagement authorization records.

AUD-08. `authorize` wrote to a predictable sibling path (`<engagement>.tmp`) with
default permissions and no fsync. That let a concurrent or hostile local process
collide with or pre-create the temp path, and a crash mid-write could leave a
truncated authorization on disk.

aegis_rt is packaged and distributed independently of the exercise harness, so it
carries its own copy rather than importing across a team boundary.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write_text(target: Path, data: str, *, mode: int = 0o600) -> None:
    """Write `data` to `target` via a unique fsynced temp file in the same directory."""
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
