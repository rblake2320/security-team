import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aegis_rt.checks.base import ExecutionContext
from aegis_rt.checks.dependency_scan import DependencyVulnerabilityCheck
from aegis_rt.models import Limits, Target, TargetKind

# Real pip-audit --format json shape, captured against a genuinely vulnerable pin
# (requests==2.6.0) during development - not hand-invented. Kept minimal deliberately.
_VULN_REPORT = {
    "dependencies": [
        {
            "name": "requests",
            "version": "2.6.0",
            "vulns": [{
                "id": "PYSEC-2018-28",
                "fix_versions": ["2.20.0"],
                "aliases": ["CVE-2018-18074"],
                "description": "Requests before 2.20.0 leaks Authorization on redirect.",
            }],
        },
    ],
    "fixes": [],
}
_CLEAN_REPORT = {
    "dependencies": [{"name": "cryptography", "version": "50.0.0", "vulns": []}],
    "fixes": [],
}


class DependencyVulnerabilityCheckTests(unittest.TestCase):
    def _context(self, root: Path, **limits) -> ExecutionContext:
        return ExecutionContext(Limits(**limits), root / "STOP")

    @patch.object(DependencyVulnerabilityCheck, "_audit", return_value=_VULN_REPORT)
    def test_known_vulnerable_pin_produces_finding(self, mock_audit):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests==2.6.0\n", encoding="utf-8")
            result = DependencyVulnerabilityCheck().run(
                Target(TargetKind.PATH, str(root)), self._context(root))
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(result.findings), 1)
            finding = result.findings[0]
            self.assertEqual(finding.evidence["vulnerability_id"], "PYSEC-2018-28")
            self.assertEqual(finding.evidence["package"], "requests")
            self.assertIn("2.20.0", finding.remediation)
            mock_audit.assert_called_once()

    @patch.object(DependencyVulnerabilityCheck, "_audit", return_value=_CLEAN_REPORT)
    def test_clean_pins_produce_no_findings(self, mock_audit):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("cryptography==50.0.0\n", encoding="utf-8")
            result = DependencyVulnerabilityCheck().run(
                Target(TargetKind.PATH, str(root)), self._context(root))
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.findings, ())

    def test_no_requirements_files_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "readme.md").write_text("nothing relevant here", encoding="utf-8")
            result = DependencyVulnerabilityCheck().run(
                Target(TargetKind.PATH, str(root)), self._context(root))
            self.assertEqual(result.status, "not_applicable")
            self.assertEqual(result.findings, ())

    @patch.object(DependencyVulnerabilityCheck, "_audit", side_effect=ValueError("advisory service unreachable"))
    def test_audit_failure_is_reported_not_raised(self, mock_audit):
        """A real subprocess/network failure must surface as an INFO finding, not crash
        the whole engagement - one unreachable advisory service shouldn't take down
        every other check in the run."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests==2.6.0\n", encoding="utf-8")
            result = DependencyVulnerabilityCheck().run(
                Target(TargetKind.PATH, str(root)), self._context(root))
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(result.findings), 1)
            self.assertEqual(result.findings[0].severity.value, "info")

    @patch.object(DependencyVulnerabilityCheck, "_audit", return_value=_VULN_REPORT)
    def test_kill_switch_stops_scan(self, mock_audit):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests==2.6.0\n", encoding="utf-8")
            stop = root / "STOP"
            stop.touch()
            context = ExecutionContext(Limits(), stop)
            with self.assertRaises(InterruptedError):
                DependencyVulnerabilityCheck().run(Target(TargetKind.PATH, str(root)), context)

    @patch.object(DependencyVulnerabilityCheck, "_audit", return_value=_VULN_REPORT)
    def test_finding_budget_truncates(self, mock_audit):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests==2.6.0\n", encoding="utf-8")
            (root / "requirements-dev.txt").write_text("requests==2.6.0\n", encoding="utf-8")
            result = DependencyVulnerabilityCheck().run(
                Target(TargetKind.PATH, str(root)), self._context(root, max_findings=1))
            self.assertEqual(result.status, "truncated")
            self.assertEqual(len(result.findings), 1)

    def test_real_pip_audit_output_shape_still_matches_mocked_fixture(self):
        """Guards against the mocked fixtures above drifting from pip-audit's actual
        output shape (the exact class of bug this whole program just spent a day
        chasing: local vs. CI vs. mocked environments silently disagreeing). Runs the
        real subprocess once, against an intentionally old, known-vulnerable pin, and
        checks only the STRUCTURE the check code depends on - not exact vuln IDs, which
        pip-audit's upstream advisory data can add to over time."""
        check = DependencyVulnerabilityCheck()
        try:
            report = check._audit("requests==2.6.0\n")
        except (OSError, ValueError) as exc:
            self.skipTest(f"advisory service unreachable in this environment: {exc}")
        self.assertIn("dependencies", report)
        dep = next((d for d in report["dependencies"] if d["name"] == "requests"), None)
        self.assertIsNotNone(dep, "requests not found in pip-audit's own dependency list")
        self.assertGreater(len(dep["vulns"]), 0, "requests==2.6.0 has publicly known CVEs")
        vuln = dep["vulns"][0]
        for key in ("id", "fix_versions", "aliases", "description"):
            self.assertIn(key, vuln)


if __name__ == "__main__":
    unittest.main()
