from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aegis_purple.assurance import evaluate_claims, evaluate_readiness
from aegis_purple.errors import ConfigurationError
from aegis_purple.scoring import score_assessment

ROOT = Path(__file__).resolve().parents[2]


# AUD-01: score_assessment derives readiness from the authoritative registry.
# Tests supply a registry, never a caller-controlled boolean.
_GATES = ["exercise_assurance_operational", "key_custody_verified"]
_PENDING_REGISTRY = {
    "assessment_readiness": {"required_gates": _GATES},
    "gate_definitions": {g: {"status": "PENDING"} for g in _GATES},
}
_VERIFIED_REGISTRY = {
    "assessment_readiness": {"required_gates": _GATES},
    "gate_definitions": {g: {"status": "VERIFIED"} for g in _GATES},
}


class AssuranceTests(unittest.TestCase):
    def test_current_readiness_holds_assurance(self) -> None:
        result = evaluate_readiness(ROOT / "00-shared" / "config" / "assessment_readiness.json")
        self.assertFalse(result["ready"])
        self.assertEqual(result["marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")

    def test_operational_claim_rejected_when_not_ready(self) -> None:
        source = json.loads((ROOT / "00-shared" / "config" / "assurance_claims.json").read_text())
        source["claims"][0]["status"] = "OPERATIONAL"
        source["claims"][0]["independent_reviewer"] = "independent-reviewer"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claims.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            result = evaluate_claims(path, readiness_ready=False)
        self.assertFalse(result["valid"])

    def test_verified_gate_without_evidence_is_rejected(self) -> None:
        source = json.loads((ROOT / "00-shared" / "config" / "assessment_readiness.json").read_text())
        source["gate_definitions"]["canonical_implementation_selected"].pop("evidence")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "readiness.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                evaluate_readiness(path)

    def test_auto_fail_zeroes_score_before_aggregation(self) -> None:
        scorecard = json.loads((ROOT / "purple-team" / "config" / "scorecard.json").read_text())
        components = {name: 1.0 for name in scorecard["components"]}
        evidence = {name: [f"EV-{name}"] for name in scorecard["components"]}
        result = score_assessment(
            scorecard, components, evidence,
            triggered_auto_failures=["any unresolved critical detection gap at exercise close"],
            readiness=_PENDING_REGISTRY, claims={},
        )
        self.assertEqual(result["diagnostic_score"], 1.0)
        self.assertEqual(result["final_score"], 0.0)
        self.assertFalse(result["passed"])

    def test_missing_evidence_cannot_receive_score(self) -> None:
        scorecard = json.loads((ROOT / "purple-team" / "config" / "scorecard.json").read_text())
        components = {name: 0.9 for name in scorecard["components"]}
        evidence = {name: [f"EV-{name}"] for name in scorecard["components"]}
        evidence["D"] = []
        with self.assertRaises(ConfigurationError):
            score_assessment(scorecard, components, evidence, triggered_auto_failures=[], readiness=_PENDING_REGISTRY, claims={})

    def test_boolean_score_is_rejected(self) -> None:
        scorecard = json.loads((ROOT / "purple-team" / "config" / "scorecard.json").read_text())
        components = {name: 0.9 for name in scorecard["components"]}
        components["C"] = True
        evidence = {name: [f"EV-{name}"] for name in scorecard["components"]}
        with self.assertRaises(ConfigurationError):
            score_assessment(scorecard, components, evidence, triggered_auto_failures=[], readiness=_PENDING_REGISTRY, claims={})


if __name__ == "__main__":
    unittest.main()
