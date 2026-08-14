"""RESIDUAL-HIGH race-injection tests for the offline scanners.

The external assessment flagged a time-of-check/time-of-use gap: the scanners
resolved a path, validated it was inside the authorized root, then performed
SEPARATE stat and read calls against that path. A hostile local writer could swap
the path between the check and the use and have the scanner read a file outside the
authorized scope. For a red-team tool the root IS the authorization boundary.

A timing-dependent test would be flaky and would prove little when it passed. These
tests instead inject the swap DETERMINISTICALLY at the exact moment the real
scanner is mid-loop - by doing the swap inside `assert_running()`, which the scanner
calls once per entry. That is the attacker winning the race every single time: the
strongest case, not a lucky one.

Nothing is mocked. Real files, real symlinks/junctions, the real check classes.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from aegis_rt.checks.base import ExecutionContext
from aegis_rt.checks.repository_posture import RepositoryPostureCheck
from aegis_rt.checks.safe_scan import (
    TraversalLimitExceeded,
    read_verified,
    walk_scope,
)
from aegis_rt.checks.source import SourceStaticCheck
from aegis_rt.models import Limits, Target, TargetKind

SECRET = 'password = "super-secret-value-outside-scope"\n'


def _link_dir(link: Path, destination: Path) -> bool:
    """Create a directory link. Junction on Windows, symlink elsewhere."""
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(destination)],
            capture_output=True, text=True, check=False, timeout=10)
        return result.returncode == 0
    link.symlink_to(destination, target_is_directory=True)
    return True


def _link_file(link: Path, destination: Path) -> bool:
    try:
        link.symlink_to(destination)
        return True
    except (OSError, NotImplementedError):
        return False  # Windows without developer mode / SeCreateSymbolicLink


class SwapContext(ExecutionContext):
    """An ExecutionContext that performs a filesystem swap mid-scan.

    `assert_running()` is called by the scanner once per entry, i.e. after traversal
    has validated the entry and before the file is read. Swapping there reproduces
    the exact window the finding describes.
    """

    def __init__(self, limits: Limits, kill_switch: Path, victim: Path,
                 attacker_payload: Path) -> None:
        super().__init__(limits, kill_switch)
        self._victim = victim
        self._payload = attacker_payload
        self.swapped = False

    def assert_running(self) -> None:  # type: ignore[override]
        super().assert_running()
        if not self.swapped and self._victim.exists():
            self.swapped = True
            self._victim.unlink()
            # Prefer a symlink out of scope - the literal finding. Where the platform
            # forbids unprivileged symlinks (Windows without SeCreateSymbolicLink),
            # fall back to a REAL replacement file holding the same out-of-scope
            # content. Both are the same defect: content that was never validated
            # being read at the validated path. The fallback keeps this test
            # meaningful everywhere rather than silently degrading to a skip.
            if not _link_file(self._victim, self._payload):
                self._victim.write_text(
                    self._payload.read_text(encoding="utf-8"), encoding="utf-8")


class ReadVerifiedTests(unittest.TestCase):
    """Direct tests of the inode binding that closes the window."""

    def test_replaced_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            victim = root / "target.py"
            victim.write_text("original\n", encoding="utf-8")
            expected = victim.lstat()

            # The attacker replaces the file with a DIFFERENT one after the check.
            victim.unlink()
            victim.write_text(SECRET, encoding="utf-8")

            self.assertIsNone(
                read_verified(victim, expected, max_bytes=1_000_000),
                "a file replaced after validation must not be read",
            )

    def test_same_size_replacement_is_refused(self) -> None:
        """The hard case: the swapped-in file is byte-for-byte the same LENGTH.

        Without this, `test_replaced_file_is_refused` could pass on a size comparison
        alone and the real discriminator would go untested. Linux inode reuse means
        (st_dev, st_ino) may also match here, so ctime_ns is what must carry it.
        """
        with tempfile.TemporaryDirectory() as directory:
            victim = Path(directory) / "target.py"
            victim.write_text("A" * 64, encoding="utf-8")
            expected = victim.lstat()

            victim.unlink()
            victim.write_text("B" * 64, encoding="utf-8")   # identical size
            self.assertEqual(victim.lstat().st_size, expected.st_size,
                             "precondition: the replacement is the same size")

            self.assertIsNone(
                read_verified(victim, expected, max_bytes=1_000_000),
                "a same-size replacement must still be refused",
            )

    def test_unchanged_file_is_still_read(self) -> None:
        """The guard must not be so strict that it refuses legitimate reads."""
        with tempfile.TemporaryDirectory() as directory:
            victim = Path(directory) / "target.py"
            victim.write_text("legitimate\n", encoding="utf-8")
            self.assertEqual(
                read_verified(victim, victim.lstat(), max_bytes=1_000_000),
                "legitimate\n",
            )

    def test_symlink_swapped_in_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "outside.py"
            outside.write_text(SECRET, encoding="utf-8")

            victim = root / "target.py"
            victim.write_text("original\n", encoding="utf-8")
            expected = victim.lstat()

            victim.unlink()
            if not _link_file(victim, outside):
                self.skipTest("symlink creation unavailable in this environment")

            self.assertIsNone(
                read_verified(victim, expected, max_bytes=1_000_000),
                "a symlink swapped in after validation must not be followed",
            )

    def test_oversized_file_is_refused_by_descriptor_not_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            victim = Path(directory) / "big.py"
            victim.write_text("x" * 5000, encoding="utf-8")
            self.assertIsNone(read_verified(victim, victim.lstat(), max_bytes=1000))


class TraversalTests(unittest.TestCase):
    def test_directory_link_out_of_scope_is_not_traversed(self) -> None:
        """Junctions must be excluded too - `is_symlink()` reports False for them."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "outside"
            outside.mkdir()
            (outside / "secret.py").write_text(SECRET, encoding="utf-8")

            if not _link_dir(root / "linked", outside):
                self.skipTest("directory link creation unavailable in this environment")

            found = [path.name for path, _ in walk_scope(root)]
            self.assertNotIn("secret.py", found,
                             "traversal must not descend through an out-of-scope link")

    def test_traversal_limit_refuses_rather_than_truncating(self) -> None:
        """Silent truncation would let an attacker hide files by padding the tree."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(12):
                (root / f"file{index}.py").write_text("x\n", encoding="utf-8")
            with self.assertRaises(TraversalLimitExceeded):
                list(walk_scope(root, max_entries=5))


class ScannerRaceInjectionTests(unittest.TestCase):
    """End-to-end: the swap happens inside the real scanner's own loop."""

    def _limits(self) -> Limits:
        return Limits(max_files=100, max_findings=50)

    def test_source_scan_does_not_read_swapped_in_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "outside.py"
            outside.write_text(SECRET, encoding="utf-8")

            victim = root / "app.py"
            victim.write_text("clean = 1\n", encoding="utf-8")

            context = SwapContext(self._limits(), root / "STOP", victim, outside)
            result = SourceStaticCheck().run(
                Target(kind=TargetKind.PATH, value=str(root)), context)

            self.assertTrue(context.swapped, "the injection did not fire")

            self.assertEqual(
                result.findings, (),
                "scanner read a file swapped in mid-scan - the TOCTOU window is open",
            )

    def test_repository_scan_does_not_read_swapped_in_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "requirements.txt"
            outside.write_text("danger>=1\n", encoding="utf-8")

            victim = root / "requirements.txt"
            victim.write_text("requests==2.32.5\n", encoding="utf-8")

            context = SwapContext(self._limits(), root / "STOP", victim, outside)
            result = RepositoryPostureCheck().run(
                Target(kind=TargetKind.PATH, value=str(root)), context)

            self.assertTrue(context.swapped, "the injection did not fire")

            self.assertEqual(
                result.findings, (),
                "scanner read an out-of-scope file swapped in mid-scan",
            )


if __name__ == "__main__":
    unittest.main()
