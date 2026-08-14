"""Falsification tests for PROGRAM-CI-SEPARATION-001.

The readiness hold depends on two workflows meaning different things:

    engineering-integrity.yml   may pass with a documented hold  (--allow-not-ready)
    assessment-issuance.yml     must fail closed                 (--require-ready)

That separation was correct when written and was protected by nothing. A single
copy-paste of `--allow-not-ready` into the issuance workflow would silently convert
the assurance gate into an advisory one, and every other control would still pass.

These tests make the separation a mechanism rather than a convention.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
ENGINEERING = WORKFLOWS / "engineering-integrity.yml"
ISSUANCE = WORKFLOWS / "assessment-issuance.yml"

HOLD_FLAG = "--allow-not-ready"
READY_FLAG = "--require-ready"


class CiSeparationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.assertTrue(WORKFLOWS.is_dir(), "CI workflow directory is missing")
        self.engineering = ENGINEERING.read_text(encoding="utf-8")
        self.issuance = ISSUANCE.read_text(encoding="utf-8")

    # --- the load-bearing assertion -------------------------------------
    def test_issuance_workflow_never_permits_a_readiness_hold(self):
        """NEGATIVE. The assurance path must not be able to pass while gates are false."""
        self.assertNotIn(
            HOLD_FLAG, self.issuance,
            f"{ISSUANCE.name} contains {HOLD_FLAG}: the assurance gate has been converted "
            "into an advisory check. This is a control failure, not a CI preference.")

    def test_issuance_workflow_requires_readiness(self):
        self.assertIn(
            READY_FLAG, self.issuance,
            f"{ISSUANCE.name} must invoke validation with {READY_FLAG} so it fails closed")

    # --- the documented exception ---------------------------------------
    def test_engineering_workflow_may_hold_but_must_be_explicit(self):
        """Engineering CI is allowed to pass under a hold - but only explicitly."""
        self.assertIn(
            HOLD_FLAG, self.engineering,
            "engineering CI should declare its hold explicitly rather than omitting the check")

    def test_engineering_workflow_does_not_claim_readiness(self):
        """NEGATIVE. Engineering CI must not assert readiness it cannot establish."""
        self.assertNotIn(
            READY_FLAG, self.engineering,
            "engineering CI must not run the assurance-grade gate; that is the issuance path")

    # --- both paths must actually exist ---------------------------------
    def test_both_workflows_exist(self):
        for path in (ENGINEERING, ISSUANCE):
            with self.subTest(workflow=path.name):
                self.assertTrue(path.is_file(), f"{path.name} is missing")

    def test_no_third_workflow_silently_issues_assurance(self):
        """NEGATIVE. A new workflow must not invoke the assurance gate under a hold."""
        for wf in sorted(WORKFLOWS.glob("*.yml")):
            text = wf.read_text(encoding="utf-8")
            with self.subTest(workflow=wf.name):
                if READY_FLAG in text:
                    self.assertNotIn(
                        HOLD_FLAG, text,
                        f"{wf.name} combines {READY_FLAG} with {HOLD_FLAG}; "
                        "a workflow may require readiness or permit a hold, never both")


if __name__ == "__main__":
    unittest.main(verbosity=2)
