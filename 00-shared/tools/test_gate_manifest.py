"""Falsification tests for PROGRAM-GATE-MANIFEST-001.

Two hand-maintained gate lists always diverge. Before this guard, the local runner
and the GitHub workflow each carried their own copy: a gate could be added to one
and silently omitted from the other, so CI would run less than the developer did
while both reported green.

The manifest at 00-shared/config/ci_gates.json is the single source of truth. These
tests fail when the workflow no longer covers it.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROGRAM = TOOLS.parents[1]
MANIFEST = PROGRAM / "00-shared" / "config" / "ci_gates.json"


def repo_root() -> Path | None:
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       cwd=str(PROGRAM), capture_output=True, text=True)
    return Path(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


ENGINEERING_WORKFLOW = "engineering-integrity.yml"


def workflow_text() -> str | None:
    """The engineering workflow at the repository root.

    The program is now its own repository, so <repo-root>/.github/workflows/ IS the
    program's workflow directory. The former `purple-team-integrity.yml` existed only
    to bridge the nesting problem (the program used to live inside another repo, where
    a nested workflow was inert). That bridge is no longer needed."""
    root = repo_root()
    if root is None:
        return None
    wf = root / ".github" / "workflows" / ENGINEERING_WORKFLOW
    return wf.read_text(encoding="utf-8") if wf.is_file() else None


class GateManifestTests(unittest.TestCase):

    def setUp(self) -> None:
        self.doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.engineering = self.doc["engineering_gates"]
        self.assurance = self.doc["assurance_gates"]

    def test_manifest_is_well_formed(self):
        self.assertGreater(len(self.engineering), 0)
        ids = [g["id"] for g in self.engineering]
        self.assertEqual(len(ids), len(set(ids)), "duplicate gate ids")
        for g in self.engineering + self.assurance:
            with self.subTest(gate=g["id"]):
                self.assertIn(g["kind"], {"unittest", "command"})
                if g["kind"] == "unittest":
                    self.assertTrue((PROGRAM / g["path"]).is_dir(),
                                    f"gate path missing: {g['path']}")
                else:
                    self.assertTrue((PROGRAM / g["argv"][0]).is_file(),
                                    f"gate command missing: {g['argv'][0]}")

    def test_workflow_covers_every_engineering_gate(self):
        """NEGATIVE. A gate in the manifest but not in the workflow means CI runs less
        than the local runner, while both report green."""
        text = workflow_text()
        if text is None:
            self.skipTest("root workflow not present (covered by test_repo_hygiene)")
        missing = []
        for gate in self.engineering:
            token = gate["pattern"] if gate["kind"] == "unittest" else Path(gate["argv"][0]).name
            probe = gate["path"] if gate["kind"] == "unittest" and gate["pattern"] == "test_*.py" else token
            if probe not in text:
                missing.append(f"{gate['id']} (looked for {probe!r})")
        self.assertEqual(missing, [],
                         "root workflow does not cover manifest gates: " + ", ".join(missing))

    def test_workflow_pins_actions_to_sha(self):
        """NEGATIVE. Mutable action tags are a supply-chain risk; the program's own
        nested workflow pinned to SHA, so the root workflow must not regress."""
        text = workflow_text()
        if text is None:
            self.skipTest("root workflow not present")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                ref = stripped.split("uses:", 1)[1].strip()
                with self.subTest(action=ref):
                    sha = ref.split("@")[-1].split()[0]
                    self.assertEqual(len(sha), 40,
                                     f"action {ref!r} is not pinned to a 40-char commit SHA")
                    int(sha, 16)  # raises if not hex

    def test_workflow_installs_hash_pinned_requirements(self):
        """NEGATIVE. Unpinned `pip install` in CI is a supply-chain hole."""
        text = workflow_text()
        if text is None:
            self.skipTest("root workflow not present")
        self.assertIn("--require-hashes", text,
                      "CI must install dependencies with --require-hashes")
        self.assertNotIn("pip install --upgrade pip cryptography pyyaml", text,
                         "unpinned dependency install present in workflow")

    def test_assurance_gate_is_not_in_the_engineering_list(self):
        """NEGATIVE. The fail-closed gate must never be run under the hold path."""
        eng_ids = {g["id"] for g in self.engineering}
        for g in self.assurance:
            with self.subTest(gate=g["id"]):
                self.assertNotIn(g["id"], eng_ids)
                self.assertNotIn("--allow-not-ready", g.get("argv", []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
