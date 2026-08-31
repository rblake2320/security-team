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
                self.assertIsInstance(g.get("sandbox_copy", False), bool,
                                      "sandbox_copy must be a boolean when present")
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


class ReadinessDerivationTests(unittest.TestCase):
    """OPUS-F6: readiness must derive from gate_definitions, not required_gates.

    Reproduced before the fix: deleting the two PENDING entries from `required_gates`
    - WITHOUT changing their status, which still read PENDING - flipped the program
    from NOT_ASSESSMENT_READY to ASSESSMENT_READY with allow_assurance_statement true,
    and made R6 unreachable. The exact negation of PROGRAM-READINESS-GATE-001.
    """

    def _gates(self):
        import copy
        import json as _json
        import os as _os
        import sys as _sys
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        import claim_check as cc
        with open(cc.GATES, encoding="utf-8") as handle:
            return cc, copy.deepcopy(_json.load(handle))

    def test_dropping_a_pending_gate_from_required_gates_cannot_buy_readiness(self):
        cc, gates = self._gates()
        pending = [n for n, d in gates["gate_definitions"].items()
                   if d.get("status") != "VERIFIED"]
        self.assertTrue(pending, "fixture must have at least one pending gate")
        gates["assessment_readiness"]["required_gates"] = [
            n for n, d in gates["gate_definitions"].items() if d.get("status") == "VERIFIED"]
        failed, _ = cc.check_gates(gates)
        for name in pending:
            self.assertIn(name, failed,
                          "a PENDING gate omitted from required_gates must still fail")

    def test_emptying_required_gates_cannot_buy_readiness(self):
        cc, gates = self._gates()
        gates["assessment_readiness"]["required_gates"] = []
        failed, _ = cc.check_gates(gates)
        self.assertEqual(sorted(failed), sorted(gates["gate_definitions"]),
                         "an empty required_gates list must fail every defined gate")

    def test_all_verified_still_reaches_readiness(self):
        """The fix must not make readiness unreachable."""
        cc, gates = self._gates()
        for d in gates["gate_definitions"].values():
            d["status"] = "VERIFIED"
        failed, _ = cc.check_gates(gates)
        self.assertEqual(failed, [], "genuinely verified gates must still pass")


class ClaimGateDoesNotMutateTreeTests(unittest.TestCase):
    """R2-F9: the gate must never write to the artifacts it verifies.

    Reproduced before the fix: one claim_check run left three files modified -
    exercise/white/authorization.json, environment_attestation.json, and an EVIDENCE
    receipt - each a changed signature. The gate was minting fresh signatures for the
    signed authorization it exists to verify, which means signing authority was live
    in the verification environment and a clean tree could never be a CI precondition.

    Introduced by the F1 fix (running the suites) and widened from 2 files to 3 by
    moving to -v. Suites now execute against a throwaway copy.

    STRUCTURAL NOTE: this test itself caused a SEPARATE, more severe incident -
    unbounded recursive process spawning, since claim_check.py's own evidence
    collection runs this very package and this test spawns claim_check.py. It now
    self-skips via CLAIM_CHECK_RECURSION_GUARD whenever it detects it is running
    inside claim_check's own evidence-collection pass. Consequence: this test can
    NEVER be cited as R5-verified evidence for any claim - from claim_check's own
    perspective it always appears SKIPPED, because resolving evidence is exactly the
    context in which it must refuse to run. This is intentional, not a gap; the
    property it tests is instead verified directly by `run_ci.py`'s gate-drift step
    and by manual `pytest 00-shared/tools`, neither of which set the guard.
    """

    def test_full_gate_run_leaves_the_tree_unmodified(self):
        import os as _os
        import subprocess as _sp
        import sys as _sys

        # CRITICAL RECURSION GUARD, checked FIRST, before anything else in this
        # method. claim_check.py's own evidence collection runs the "00-shared/tools"
        # package - which is THIS file. Without this check, this test spawns
        # claim_check.py, whose collect_node_ids() runs this package again, hitting
        # this same test again, spawning claim_check.py again: unbounded recursive
        # process spawning. Measured live: 100+ python.exe processes, tens of GB of
        # RAM, in under 4 minutes, reachable through completely ordinary
        # `run_ci.py` execution. claim_check.py sets CLAIM_CHECK_RECURSION_GUARD in
        # the environment of every subprocess its own evidence collection spawns;
        # seeing it here means we ARE that spawned subprocess, and must not spawn
        # another one. (There is also a second, independent guard inside
        # collect_node_ids() itself - defense in depth, not a substitute for this one.)
        if _os.environ.get("CLAIM_CHECK_RECURSION_GUARD"):
            self.skipTest(
                "running inside claim_check's own evidence collection; spawning "
                "another claim_check.py here would recurse unboundedly")

        root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        if _sp.run(["git", "rev-parse", "--git-dir"], cwd=root,
                   capture_output=True).returncode != 0:
            self.skipTest("not a git checkout")

        before = _sp.run(["git", "status", "--porcelain"], cwd=root,
                         capture_output=True, text=True).stdout
        _sp.run([_sys.executable, _os.path.join("00-shared", "tools", "claim_check.py")],
                cwd=root, capture_output=True, text=True, timeout=900)
        after = _sp.run(["git", "status", "--porcelain"], cwd=root,
                        capture_output=True, text=True).stdout

        self.assertEqual(
            sorted(after.splitlines()), sorted(before.splitlines()),
            "claim_check modified the working tree; a gate must not write to what it "
            "verifies",
        )
