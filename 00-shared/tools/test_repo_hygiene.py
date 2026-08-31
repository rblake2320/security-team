"""Falsification tests for PROGRAM-REPO-HYGIENE-001 and PROGRAM-CI-REACHABLE-001.

Two defects found on 2026-08-14, both of the same class as everything else in this
program: a mechanism asserted, never demonstrated.

  1. The entire Purple team directory was UNTRACKED. 200+ files, 157 tests, no
     version control, no history, no backup.
  2. The CI workflows sat at `.github/workflows/`. GitHub Actions only
     reads `<repo-root>/.github/workflows/`, and the repo root was the parent
     workspace, not this directory.
     The workflows had never run and COULD not run. Every claim whose evidence was
     "CI enforces X" was therefore unevidenced.

These tests make both conditions checkable rather than assumed.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROGRAM = TOOLS.parents[1]                      # .../Purple team


def git(*args: str, cwd: Path) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def repo_root() -> Path | None:
    code, out = git("rev-parse", "--show-toplevel", cwd=PROGRAM)
    return Path(out.strip()) if code == 0 and out.strip() else None


SECRET_PATTERNS = ("_fixture_private_keys", ".pem", ".key", "_private")


def detect_leaks(tracked_files: list[str]) -> list[str]:
    """Return secret-shaped paths. Extracted so it can be falsified directly."""
    return [f for f in tracked_files if any(pat in f.lower() for pat in SECRET_PATTERNS)]


class RepoHygieneTests(unittest.TestCase):
    """Secrets must never enter version control."""

    def test_fixture_private_keys_exist_but_are_ignored(self):
        """The fixture keys are needed on disk and must be excluded from git."""
        keys = PROGRAM / "exercise" / "tests" / "fixtures" / "trust" / "_fixture_private_keys.json"
        gen = PROGRAM / "exercise" / "tests" / "fixtures" / "make_fixture_trust.py"
        self.assertTrue(gen.is_file(),
                        "a fresh clone must be able to GENERATE fixture trust material; "
                        "committed public keys with gitignored private keys are unusable")
        root = repo_root()
        if root is None:
            self.skipTest("not a git repository")
        if not keys.is_file():
            return   # fresh clone: absence is correct, the generator supplies them
        code, _ = git("check-ignore", "-q", str(keys), cwd=root)
        self.assertEqual(code, 0,
                         "fixture private keys are NOT gitignored; committing would place "
                         "private keys in git history permanently")

    def test_no_secret_material_is_tracked(self):
        """NEGATIVE. Nothing matching a secret pattern may be tracked."""
        root = repo_root()
        if root is None:
            self.skipTest("not a git repository")
        rel = PROGRAM.relative_to(root).as_posix()
        code, out = git("ls-files", rel, cwd=root)
        if code != 0:
            self.skipTest("git ls-files unavailable")
        leaked = detect_leaks(out.splitlines())
        self.assertEqual(leaked, [],
                         f"secret-shaped files are tracked in git: {leaked}")

    def test_detector_rejects_secret_shaped_paths(self):
        """NEGATIVE / FALSIFICATION. A clean repository proves nothing unless the
        detector actually catches a leak. Feed it poisoned input and require a catch."""
        poisoned = [
            "exercise/tests/fixtures/trust/_fixture_private_keys.json",
            "authority.pem",
            "keys/clearance.key",
            "config/white_private_signing.json",
            "EXERCISE/TESTS/FIXTURES/TRUST/_FIXTURE_PRIVATE_KEYS.JSON",  # case
        ]
        for path in poisoned:
            with self.subTest(leak=path):
                self.assertEqual(detect_leaks([path]), [path],
                                 f"detector FAILED to catch a secret-shaped path: {path}")

    def test_detector_does_not_flag_ordinary_files(self):
        """NEGATIVE. A detector that flags everything is equally useless."""
        benign = [
            "README.md",
            "exercise/tests/fixtures/trust/fixture-white-2026.json",  # public key
            "00-shared/config/assurance_claims.json",
            "red-team/src/aegis_rt/authorization.py",
        ]
        self.assertEqual(detect_leaks(benign), [],
                         "detector produced false positives on ordinary files")

    def test_gitignore_exists_and_covers_secrets(self):
        gi = PROGRAM / ".gitignore"
        self.assertTrue(gi.is_file(), "the program directory must carry its own .gitignore")
        text = gi.read_text(encoding="utf-8")
        for needle in ("_fixture_private_keys.json", "*.pem", "used_nonces.json"):
            with self.subTest(rule=needle):
                self.assertIn(needle, text)


class CiReachabilityTests(unittest.TestCase):
    """A workflow GitHub never reads is not a control."""

    def test_program_workflows_are_reachable_by_ci(self):
        """The load-bearing assertion.

        GitHub Actions reads ONLY `<repo-root>/.github/workflows/`. A workflow in a
        nested directory is inert. If the program keeps its own workflow copies, an
        equivalent must exist at the repository root.
        """
        root = repo_root()
        if root is None:
            self.skipTest("not a git repository")
        if root.resolve() == PROGRAM.resolve():
            return  # program IS the repo root; its workflows are reachable

        root_wf = root / ".github" / "workflows"
        self.assertTrue(root_wf.is_dir(),
                        f"repo root {root} has no .github/workflows; program CI cannot run")
        names = {p.name for p in root_wf.glob("*.yml")} | {p.name for p in root_wf.glob("*.yaml")}
        self.assertIn(
            "engineering-integrity.yml", names,
            "the program's CI workflow is not present at the repository root, so GitHub "
            "Actions will never execute it. A workflow file in a nested directory is inert.")

    def test_root_workflow_actually_invokes_the_program_gates(self):
        """A reachable workflow that runs nothing is equally useless."""
        root = repo_root()
        if root is None:
            self.skipTest("not a git repository")
        wf = root / ".github" / "workflows" / "engineering-integrity.yml"
        if not wf.is_file():
            self.skipTest("root workflow not yet installed (see test above)")
        text = wf.read_text(encoding="utf-8")
        for needed in ("claim_check.py", "test_ci_integrity", "unittest"):
            with self.subTest(invokes=needed):
                self.assertIn(needed, text)

    def test_external_github_actions_are_pinned_to_full_commits(self):
        """A mutable action tag can silently change executable CI code."""
        root = repo_root()
        if root is None:
            self.skipTest("not a git repository")
        workflow_root = root / ".github" / "workflows"
        workflows = sorted(workflow_root.glob("*.yml")) + sorted(workflow_root.glob("*.yaml"))
        self.assertTrue(workflows, "repository has no reachable workflows")
        unpinned: list[str] = []
        for workflow in workflows:
            text = workflow.read_text(encoding="utf-8")
            for action, reference in re.findall(
                r"(?m)^\s*-?\s*uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)",
                text,
            ):
                if not re.fullmatch(r"[0-9a-f]{40}", reference):
                    unpinned.append(f"{workflow.name}: {action}@{reference}")
        self.assertEqual(unpinned, [], f"external actions are not commit-pinned: {unpinned}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
