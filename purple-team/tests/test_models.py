from __future__ import annotations

import unittest

from aegis_purple.canonical import load_json_bounded
from aegis_purple.errors import ConfigurationError
from aegis_purple.models import ExercisePlan


def plan_data() -> dict:
    return {
        "schema": "aegis.purple.exercise-plan/1.0",
        "exercise_id": "EX-2026-001",
        "version": 1,
        "title": "Identity detection validation",
        "owner": "purple-lead",
        "environment": "lab",
        "expires_at": "2026-12-31T23:59:59Z",
        "authorization_receipt_sha256": "a" * 64,
        "readiness_snapshot_sha256": "b" * 64,
        "rubric_sha256": "c" * 64,
        "role_trust_sha256": "f" * 64,
        "test_cases": [{
            "test_case_id": "TC-2026-001",
            "technique": "T1110.003",
            "procedure_sha256": "d" * 64,
            "expected_telemetry": ["identity.signin.failure"],
            "expected_detections": ["BT-IDENTITY-001"],
            "safety_class": "low",
            "rollback_verified": True,
            "observe_only": False,
        }],
        "stop_conditions": ["Any event outside the synthetic tenant"],
    }


class ModelTests(unittest.TestCase):
    def test_plan_digest_is_deterministic(self) -> None:
        first = ExercisePlan.from_dict(plan_data())
        second = ExercisePlan.from_dict(dict(reversed(list(plan_data().items()))))
        self.assertEqual(first.digest, second.digest)

    def test_unknown_plan_field_fails_closed(self) -> None:
        data = plan_data()
        data["surprise"] = True
        with self.assertRaises(ConfigurationError):
            ExercisePlan.from_dict(data)

    def test_string_false_cannot_bypass_boolean(self) -> None:
        data = plan_data()
        data["test_cases"][0]["rollback_verified"] = "false"
        with self.assertRaises(ConfigurationError):
            ExercisePlan.from_dict(data)

    def test_production_requires_observe_only(self) -> None:
        data = plan_data()
        data["environment"] = "prod"
        with self.assertRaises(ConfigurationError):
            ExercisePlan.from_dict(data)

    def test_high_safety_requires_verified_rollback(self) -> None:
        data = plan_data()
        data["test_cases"][0]["safety_class"] = "high"
        data["test_cases"][0]["rollback_verified"] = False
        with self.assertRaises(ConfigurationError):
            ExercisePlan.from_dict(data)

    def test_unicode_key_collision_is_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_json_bounded(b'{"Name": 1, "name": 2}')


if __name__ == "__main__":
    unittest.main()
