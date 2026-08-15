"""Regression test for `md_files()` scanning generated/runtime artifact directories.

Found 2026-08-15, cross-examining CI-RED failure #1 (windows-latest, non-
deterministic claim-gate violation count: 1 local / 59 earlier / 97 in CI, same
commit). `md_files()` excluded `.git`, `__pycache__`, `.ruff_cache`, and
`node_modules`, but not `.pytest_cache` - which pytest creates on first run and
seeds with its own `README.md`. Because that directory is gitignored but not
excluded from the raw filesystem walk, the R1 markdown scan's file count depended
on whether pytest had already run in that exact checkout, not on the code under
test. Independently reproduced (claude-cybersecurity, same-commit local runs) and
confirmed here: a fresh checkout scans N files; after running any pytest suite in
that checkout, it scans N+1, purely from `.pytest_cache/README.md` appearing.

This does not by itself explain CI-RED failure #1 (that failure is in R5/evidence
resolution, not R1 - see `from-claude-cybersecurity-CI-RED-progress.md`), but it is
a real, separate correctness defect: a security-relevant scanner's coverage should
never depend on incidental test-execution history.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claim_check as cc  # noqa: E402


class MdFilesArtifactExclusionTests(unittest.TestCase):
    def test_pytest_cache_readme_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-shared").mkdir()
            (root / "00-shared" / "real_doc.md").write_text("real content", encoding="utf-8")
            original_root = cc.ROOT
            cc.ROOT = str(root)
            try:
                before = cc.md_files()
                self.assertEqual(len(before), 1, "sanity: only the real doc is seen")

                pytest_cache = root / ".pytest_cache"
                pytest_cache.mkdir()
                (pytest_cache / "README.md").write_text(
                    "This directory is a cache...", encoding="utf-8"
                )

                after = cc.md_files()
                self.assertEqual(
                    len(after), 1,
                    "md_files() must not pick up .pytest_cache content - its "
                    "presence depends on test-execution history, not on the "
                    "checked-in source the scanner is meant to cover",
                )
            finally:
                cc.ROOT = original_root

    def test_other_known_exclusions_still_hold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-shared").mkdir()
            (root / "00-shared" / "real_doc.md").write_text("real content", encoding="utf-8")
            for junk_dir in (".git", "__pycache__", ".ruff_cache", "node_modules"):
                d = root / junk_dir
                d.mkdir()
                (d / "noise.md").write_text("noise", encoding="utf-8")
            original_root = cc.ROOT
            cc.ROOT = str(root)
            try:
                files = cc.md_files()
                self.assertEqual(len(files), 1, "pre-existing exclusions must still hold")
            finally:
                cc.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
