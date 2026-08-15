"""Falsification tests for PURPLE-READINESS-DERIVED-001 (AUD-01).

An external adversarial review found that `aegis-purple score --assessment-ready`
produced `marking: ASSESSMENT_CANDIDATE` and `assurance_statement_permitted: true`
while the authoritative registry said NOT_ASSESSMENT_READY.

The readiness hold is the central control of this programme. It was bypassable
with a command-line flag, because the marking was computed from a caller-supplied
boolean rather than derived from the registry. A caller-controlled boolean is not
a control.

These tests require that the derivation cannot be re-opened.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "purple-team" / "src"))

from aegis_purple.errors import ConfigurationError  # noqa: E402
from aegis_purple.scoring import score_assessment  # noqa: E402

SCORECARD = json.loads((REPO / "purple-team" / "config" / "scorecard.json").read_text(encoding="utf-8"))
READINESS = json.loads((REPO / "00-shared" / "config" / "assessment_readiness.json").read_text(encoding="utf-8"))
CLAIMS_PATH = REPO / "00-shared" / "config" / "assurance_claims.json"


def perfect_inputs() -> tuple[dict, dict]:
    names = list(SCORECARD["components"])
    return {n: 1.0 for n in names}, {n: ["EV-001"] for n in names}


def readiness_with(status: str) -> dict:
    r = copy.deepcopy(READINESS)
    for gate in r["assessment_readiness"]["required_gates"]:
        r["gate_definitions"][gate]["status"] = status
    return r


class ReadinessDerivationTests(unittest.TestCase):

    def _score(self, readiness: dict) -> dict:
        scores, refs = perfect_inputs()
        return score_assessment(SCORECARD, scores, refs,
                                triggered_auto_failures=[],
                                readiness=readiness, claims={})

    # ---------- the finding itself ----------
    def test_pending_gates_force_training_marking(self):
        """NEGATIVE. A perfect score with gates pending must NOT be an assessment candidate."""
        result = self._score(readiness_with("PENDING"))
        self.assertEqual(result["marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")
        self.assertFalse(result["assurance_statement_permitted"])
        self.assertTrue(result["pending_readiness_gates"])

    def test_one_pending_gate_is_enough_to_hold(self):
        """NEGATIVE. All-but-one verified must still hold. No partial credit."""
        r = readiness_with("VERIFIED")
        held = r["assessment_readiness"]["required_gates"][0]
        r["gate_definitions"][held]["status"] = "PENDING"
        result = self._score(r)
        self.assertFalse(result["assurance_statement_permitted"])
        self.assertEqual(result["pending_readiness_gates"], [held])

    def test_all_verified_permits_candidate(self):
        """POSITIVE. The derivation must work in both directions, or it is just a
        constant that happens to look like a control."""
        result = self._score(readiness_with("VERIFIED"))
        self.assertEqual(result["marking"], "ASSESSMENT_CANDIDATE")
        self.assertTrue(result["assurance_statement_permitted"])
        self.assertEqual(result["pending_readiness_gates"], [])

    # ---------- the interface cannot re-open it ----------
    def test_score_accepts_no_caller_supplied_readiness(self):
        """NEGATIVE. `assessment_ready=` must not be reintroduced as a parameter."""
        scores, refs = perfect_inputs()
        with self.assertRaises(TypeError):
            score_assessment(SCORECARD, scores, refs, triggered_auto_failures=[],
                             readiness=readiness_with("PENDING"), claims={},
                             assessment_ready=True)

    def test_cli_rejects_the_old_bypass_flag(self):
        """NEGATIVE. The exact command from the audit must fail."""
        proc = subprocess.run(
            [sys.executable, "-m", "aegis_purple", "score",
             "--scorecard", str(REPO / "purple-team" / "config" / "scorecard.json"),
             "--input", str(REPO / "purple-team" / "examples" / "exercise-plan.json"),
             "--assessment-ready"],
            cwd=str(REPO), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPO / "purple-team" / "src")},
        )
        self.assertNotEqual(proc.returncode, 0)
        output = proc.stdout + proc.stderr
        # The flag must be REJECTED OUTRIGHT, not merely ignored. Asserting the
        # exact rejection is stronger than asserting some error occurred.
        self.assertIn("--assessment-ready", output)
        self.assertIn("unrecognized arguments", output)
        self.assertNotIn("ASSESSMENT_CANDIDATE", proc.stdout)

    # ---------- malformed registries fail closed ----------
    def test_malformed_registry_fails_closed(self):
        """NEGATIVE. A broken registry must refuse, never default to ready."""
        scores, refs = perfect_inputs()
        for broken in ({}, {"assessment_readiness": {}}, {"gate_definitions": {}},
                       {"assessment_readiness": {"required_gates": []}, "gate_definitions": {}},
                       {"assessment_readiness": {"required_gates": ["ghost"]}, "gate_definitions": {}}):
            with self.subTest(registry=broken):
                with self.assertRaises(ConfigurationError):
                    score_assessment(SCORECARD, scores, refs, triggered_auto_failures=[],
                                     readiness=broken, claims={})

    def test_unknown_status_is_not_verified(self):
        """NEGATIVE. Only the exact string VERIFIED counts. No truthy shortcuts."""
        for status in ("verified", "Verified", "TRUE", "OK", "", "COMPLETE"):
            with self.subTest(status=status):
                result = self._score(readiness_with(status))
                self.assertFalse(result["assurance_statement_permitted"],
                                 f"status {status!r} must not satisfy the gate")

    # ---------- the score records what permitted it ----------
    def test_result_names_the_authority_and_pending_gates(self):
        result = self._score(readiness_with("PENDING"))
        self.assertEqual(result["readiness_derived_from"], "assessment_readiness.json")
        self.assertIn("pending_readiness_gates", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class ForgedRegistryTests(unittest.TestCase):
    """AUD-01b, found while attacking the AUD-01 fix.

    The first fix replaced a caller-controlled BOOLEAN with a caller-controlled
    PATH. A self-consistent forged registry - gates VERIFIED, evidence refs
    present, state_model set to ASSESSMENT_READY - passed validate_program and
    produced ASSESSMENT_CANDIDATE. The same defect wearing a different hat.

    Authority now comes from the program's own artifact. These tests require that
    no supplied path can substitute for it.
    """

    def _run(self, *extra: str):
        return subprocess.run(
            [sys.executable, "-m", "aegis_purple", "score",
             "--scorecard", str(REPO / "purple-team" / "config" / "scorecard.json"),
             "--input", str(self.input_path), *extra],
            cwd=str(REPO), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPO / "purple-team" / "src")})

    def setUp(self):
        names = list(SCORECARD["components"])
        self.input_path = REPO / "purple-team" / "tests" / "_forgery_input.json"
        self.input_path.write_text(json.dumps({
            "exercise_id": "EX-FORGERY-TEST",
            "component_scores": {n: 1.0 for n in names},
            "evidence_refs": {n: ["EV-1"] for n in names},
        }), encoding="utf-8")
        self.forged = REPO / "purple-team" / "tests" / "_forged_readiness.json"
        forged = copy.deepcopy(READINESS)
        for gate in forged["assessment_readiness"]["required_gates"]:
            forged["gate_definitions"][gate]["status"] = "VERIFIED"
            forged["gate_definitions"][gate].setdefault("evidence", []).append("README.md")
        forged.setdefault("state_model", {})["current_state"] = "ASSESSMENT_READY"
        self.forged.write_text(json.dumps(forged), encoding="utf-8")

    def tearDown(self):
        self.input_path.unlink(missing_ok=True)
        self.forged.unlink(missing_ok=True)

    def test_forged_registry_is_refused(self):
        """NEGATIVE. The exact attack that defeated the first fix."""
        proc = self._run("--readiness", str(self.forged))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("non-canonical", proc.stdout + proc.stderr)

    def test_forged_registry_never_yields_a_candidate_marking(self):
        """NEGATIVE. Belt and braces: even if it somehow ran, it must not mark."""
        proc = self._run("--readiness", str(self.forged))
        self.assertNotIn("ASSESSMENT_CANDIDATE", proc.stdout)

    def test_default_invocation_uses_the_canonical_registry(self):
        """POSITIVE. With no path supplied it reads the program's own artifact and holds."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")
        self.assertFalse(result["assurance_statement_permitted"])
        self.assertTrue(result["pending_readiness_gates"])

    def test_canonical_path_supplied_explicitly_is_accepted(self):
        """POSITIVE. Naming the real artifact is fine; only substitutes are refused."""
        proc = self._run("--readiness", str(REPO / "00-shared" / "config" / "assessment_readiness.json"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")


class RequiredGatesListTests(unittest.TestCase):
    """L3-F1 (external review, reproduced). `_readiness_state` iterated the
    author-editable `required_gates` list instead of `gate_definitions`, the record
    ground truth sits in. Dropping the two PENDING gates from that list - WITHOUT
    touching their status, which still read PENDING - made this function return
    ready=True. The exact falsification of PROGRAM-READINESS-GATE-001 that
    AUD-01/AUD-01b/claim_check-F6 each closed in a DIFFERENT module; this file had no
    owner when those landed, so the pattern survived here.
    """

    def test_dropping_pending_gates_from_required_gates_cannot_buy_readiness(self):
        from aegis_purple.scoring import _readiness_state

        registry = copy.deepcopy(READINESS)
        pending_names = [n for n, d in registry["gate_definitions"].items()
                          if d["status"] != "VERIFIED"]
        self.assertTrue(pending_names, "fixture must have at least one pending gate")

        registry["assessment_readiness"]["required_gates"] = [
            n for n, d in registry["gate_definitions"].items() if d["status"] == "VERIFIED"
        ]
        ready, pending = _readiness_state(registry)

        self.assertFalse(ready, "a PENDING gate omitted from required_gates must still hold")
        for name in pending_names:
            self.assertIn(name, pending)

    def test_narrowing_required_gates_flags_every_omission_regardless_of_status(self):
        """Omitting a gate from required_gates is a failure on its own, even a
        VERIFIED one - required_gates cannot be used to silently shrink the surface
        the registry is judged against."""
        from aegis_purple.scoring import _readiness_state

        registry = copy.deepcopy(READINESS)
        kept = list(registry["gate_definitions"])[:1]   # keep list non-empty
        registry["assessment_readiness"]["required_gates"] = kept
        ready, pending = _readiness_state(registry)

        omitted = sorted(set(registry["gate_definitions"]) - set(kept))
        still_pending = sorted(n for n, d in registry["gate_definitions"].items()
                               if d["status"] != "VERIFIED")
        self.assertEqual(sorted(pending), sorted(set(omitted) | set(still_pending)))
        self.assertFalse(ready)

    def test_all_verified_still_reaches_readiness(self):
        """POSITIVE. The fix must not make a genuinely ready registry unreachable."""
        from aegis_purple.scoring import _readiness_state

        registry = copy.deepcopy(READINESS)
        for definition in registry["gate_definitions"].values():
            definition["status"] = "VERIFIED"
        ready, pending = _readiness_state(registry)
        self.assertTrue(ready)
        self.assertEqual(pending, [])
