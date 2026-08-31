"""Falsification tests for the machine-readable application-security baseline."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
CATALOG = ROOT / "00-shared" / "config" / "application_security_baseline.json"
SPEC = importlib.util.spec_from_file_location(
    "validate_appsec_baseline", TOOLS / "validate_appsec_baseline.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ApplicationSecurityBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_repository_baseline_is_valid(self):
        self.assertEqual(MODULE.validate(self.catalog), [])

    def test_missing_control_fails_closed(self):
        poisoned = copy.deepcopy(self.catalog)
        poisoned["controls"].pop(6)
        self.assertTrue(any("exactly once in order" in item
                            for item in MODULE.validate(poisoned)))

    def test_unknown_control_field_is_rejected(self):
        poisoned = copy.deepcopy(self.catalog)
        poisoned["controls"][0]["ui_is_enough"] = True
        self.assertTrue(any("keys must be exactly" in item
                            for item in MODULE.validate(poisoned)))

    def test_control_without_negative_tests_is_rejected(self):
        poisoned = copy.deepcopy(self.catalog)
        poisoned["controls"][4]["negative_tests"] = []
        self.assertTrue(any("at least two tests" in item
                            for item in MODULE.validate(poisoned)))

    def test_catalog_cannot_point_outside_repository(self):
        poisoned = copy.deepcopy(self.catalog)
        poisoned["document"] = "../outside.md"
        self.assertTrue(any("inside the repository" in item
                            for item in MODULE.validate(poisoned)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
