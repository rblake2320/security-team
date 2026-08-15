"""Descriptor-verified, no-follow filesystem traversal for offline scanners.

RESIDUAL-HIGH (external assessment, 2026-08-14). The source and repository-posture
scanners resolved a path, validated it was inside the authorized root, and then
performed SEPARATE `stat()` and `read_text()` calls against that path. Between the
check and the use, a hostile local writer could swap the path - or a parent
component - for a symlink pointing outside the root. The scanner would then read a
file it was never authorized to touch.

For a red-team tool the authorized root IS the authorization boundary, so reading
outside it is a scope violation, not merely a bug.

Two mechanisms close the gap:

  * **Traversal never follows links.** `os.walk(followlinks=False)` plus an explicit
    symlink skip using `scandir`'s cached lstat, so no directory link can widen the
    scope. Bounded by an explicit entry limit so a link farm or deep tree cannot
    exhaust the run.
  * **The file read is bound to an inode, not a path.** The file is opened once with
    `O_NOFOLLOW` where the platform provides it, then `fstat` on the DESCRIPTOR is
    compared against the `lstat` recorded during traversal. If the path was swapped
    in between, `(st_dev, st_ino)` no longer match and the file is refused. All
    subsequent reads use that descriptor, so there is no second path lookup to race.

Windows has no `O_NOFOLLOW`, so the device/inode identity check is what carries the
guarantee there; NTFS supplies both fields. The check is therefore not
platform-conditional.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

# A scan that walks more than this many entries is refused rather than silently
# truncated - see `TraversalLimitExceeded`. Silent truncation would let an attacker
# hide files by padding the tree.
DEFAULT_MAX_ENTRIES = 200_000

_OPEN_FLAGS = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)


class TraversalLimitExceeded(RuntimeError):
    """The scan exceeded its entry budget; results would be incomplete."""


def walk_scope(root: Path, *, max_entries: int = DEFAULT_MAX_ENTRIES) -> Iterator[tuple[Path, os.stat_result]]:
    """Yield `(path, lstat)` for regular files under `root`, never following links.

    The returned `lstat` is the identity the caller must later prove the opened
    descriptor still matches. Yielding it here rather than re-stat'ing is the point:
    a second path-based stat would reintroduce the race.
    """
    seen = 0
    anchor = os.path.realpath(root)
    for directory, subdirectories, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        # Do not descend through anything that leaves the authorized root. `is_symlink`
        # alone is NOT enough: on Windows a JUNCTION is a reparse point that
        # `is_symlink()` reports as False, and `os.walk(followlinks=False)` will happily
        # descend into it. Comparing the fully resolved path against the root catches
        # symlinks, junctions, and mount points uniformly.
        kept: list[str] = []
        for name in subdirectories:
            seen += 1
            if seen > max_entries:
                raise TraversalLimitExceeded(
                    f"traversal exceeded {max_entries} entries under {root}")
            if _contained(current / name, anchor):
                kept.append(name)
        subdirectories[:] = kept

        for name in filenames:
            seen += 1
            if seen > max_entries:
                raise TraversalLimitExceeded(
                    f"traversal exceeded {max_entries} entries under {root}")
            path = current / name
            if not _contained(path, anchor):
                continue
            try:
                info = path.lstat()
            except OSError:
                continue
            # Regular files only. Symlinks, devices, and FIFOs are skipped outright:
            # a FIFO would block the scanner, a device could be enormous.
            if not _is_regular(info):
                continue
            yield path, info


def _contained(path: Path, anchor: str) -> bool:
    """True when `path` fully resolves to somewhere at or under `anchor`.

    Time-of-check only. It is what makes `read_verified`'s inode binding meaningful:
    this decides the file was in scope, the descriptor identity proves the file that
    is actually read is that same one.
    """
    try:
        resolved = os.path.realpath(path)
    except OSError:
        return False
    return resolved == anchor or resolved.startswith(anchor + os.sep)


def _identity(info: os.stat_result) -> tuple:
    """The tuple that must match between traversal-time lstat and read-time fstat.

    STABLE FIELDS ONLY. An earlier version added st_ctime_ns to defeat Linux inode
    reuse, which measured a ~10% mismatch rate on Windows between a path lstat and a
    handle fstat of the SAME unmodified file - NTFS serves the two from different
    sources. A scanner that randomly refuses 10% of files silently under-reports,
    which is a worse failure than the one being fixed.

    Dropping ctime is sound because it was defending a threat this control does not
    own. A delete-and-recreate at the same path inside the authorized root produces a
    file that is still INSIDE the root, so reading it is not a scope violation - it is
    just newer content. The property here is "never read content from outside the
    authorized root", and that is carried by O_NOFOLLOW plus (dev, ino):

      * final-component symlink out of scope -> O_NOFOLLOW refuses the open
      * hardlink SWAPPED IN AFTER traversal  -> carries that file's inode, so (dev, ino)
                                                differs from what traversal validated
      * swapped parent directory             -> resolves to a different inode, likewise

    SONNET-01 (external review, reproduced): this list previously said "hardlink to an
    out-of-scope file" without qualification. That was FALSE for a hardlink that already
    exists when the scan starts. A hardlink is not a reference to another path - it is an
    equal name for an inode - so `realpath` resolves it to its own in-root path and
    traversal validates it as in scope. The identity check then compares the file to
    itself and passes. Out-of-scope CONTENT was read. See `_multiply_linked`.
    """
    return (info.st_dev, info.st_ino, info.st_mode)


def _multiply_linked(info: os.stat_result) -> bool:
    """True when the inode has more than one name, so content may originate outside.

    There is no portable way to enumerate an inode's other names, and no notion of a
    'canonical' one - every hardlink is equally the file. So the only sound answer for a
    tool whose authorized root IS its authorization boundary is to refuse to read it.

    This is a deliberate, disclosed refusal rather than a silent skip: it is recorded in
    the limitations of AEGIS-RT-SCAN-SCOPE-001 and pinned by a regression test.
    """
    return info.st_nlink > 1


def _is_regular(info: os.stat_result) -> bool:
    import stat as _stat

    return _stat.S_ISREG(info.st_mode)


def read_verified(path: Path, expected: os.stat_result, *, max_bytes: int) -> str | None:
    """Read `path` only if it is still the exact file seen during traversal.

    Returns None when the file was swapped, is no longer regular, exceeds
    `max_bytes`, or cannot be opened. None means "skip", never "empty".
    """
    try:
        descriptor = os.open(path, _OPEN_FLAGS)
    except OSError:
        # ELOOP here means O_NOFOLLOW refused a symlink that appeared after traversal.
        return None
    try:
        actual = os.fstat(descriptor)
        if not _is_regular(actual):
            return None
        # THE check: the descriptor must be the file traversal validated as in scope.
        if _identity(actual) != _identity(expected):
            return None
        # SONNET-01: a pre-existing in-root hardlink to an out-of-scope file passes
        # every check above - realpath resolves it to its own in-root path, and the
        # identity comparison compares the file to itself. Reproduced: out-of-scope
        # content WAS read. Refuse multiply-linked files outright.
        if _multiply_linked(actual):
            return None
        # Defence in depth. The open pins the inode, so it cannot be recycled while we
        # hold the descriptor; re-stat'ing the PATH now and comparing tells us the path
        # still refers to the file we are about to read, rather than something
        # substituted between traversal and open.
        try:
            if _identity(os.lstat(path)) != _identity(actual):
                return None
        except OSError:
            return None
        if actual.st_size > max_bytes:
            return None
        data = b""
        while len(data) <= max_bytes:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            data += chunk
        if len(data) > max_bytes:
            return None
        # Reading through a descriptor means no universal-newline translation, which
        # `read_text` previously applied. Normalise explicitly so line numbers and
        # anchored patterns behave identically to before on CRLF files.
        return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    except OSError:
        return None
    finally:
        os.close(descriptor)


def within_root(path: Path, root: Path) -> bool:
    """Lexical containment check on already-link-free traversal output.

    Safe here ONLY because `walk_scope` guarantees no component is a symlink; used
    on arbitrary input it would be exactly the check this module exists to replace.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
