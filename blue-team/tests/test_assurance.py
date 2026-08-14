from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from blue_team.assurance import validate_configuration
from blue_team.errors import ConfigurationError

ROOT = Path(__file__).resolve().parents[1]


class AssuranceTests(unittest.TestCase):
    def validate(self, **overrides: Path) -> dict:
        paths = {
            "rules_path": ROOT / "rules",
            "manifest_path": ROOT / "config" / "rule_manifest.json",
            "coverage_path": ROOT / "config" / "coverage_target.json",
            "sensors_path": ROOT / "config" / "sensor_policy.json",
            "playbooks_path": ROOT / "playbooks" / "playbooks.json",
        }
        paths.update(overrides)
        return validate_configuration(**paths)

    def test_complete_configuration_passes(self) -> None:
        result = self.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["coverage_percent"], 100.0)

    def test_missing_sensor_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensors.json"
            path.write_text(json.dumps([{"source": "edr", "max_age_seconds": 60}]), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                self.validate(sensors_path=path)

    def test_high_risk_step_without_rollback_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "playbooks.json"
            path.write_text(
                json.dumps({"bad": {"steps": [{"action": "isolate_host", "description": "bad"}]}}),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                self.validate(playbooks_path=path)


if __name__ == "__main__":
    unittest.main()
