import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from aegis_rt.checks.base import ExecutionContext
from aegis_rt.checks.repository_posture import RepositoryPostureCheck
from aegis_rt.models import Limits, Target, TargetKind


class RepositoryPostureTests(unittest.TestCase):
    def test_detects_unpinned_dependency_and_write_all_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text("permissions: write-all\n", encoding="utf-8")
            result = self._run(root)
            self.assertEqual({item.evidence["rule_id"] for item in result.findings}, {
                "unpinned-dependency", "workflow-write-all",
            })

    def test_exact_dependency_and_read_only_workflow_are_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests==2.32.5\n", encoding="utf-8")
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "safe.yml").write_text("permissions:\n  contents: read\n", encoding="utf-8")
            self.assertEqual(self._run(root).findings, ())

    def test_link_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            outside_dir = base / "outside"
            outside_dir.mkdir()
            outside = outside_dir / "requirements.txt"
            outside.write_text("danger>=1\n", encoding="utf-8")
            if os.name == "nt":
                link = root / "linked"
                result = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside_dir)],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            else:
                (root / "requirements.txt").symlink_to(outside)
            self.assertEqual(self._run(root).findings, ())

    def test_finding_budget_truncates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("a>=1\nb>=1\n", encoding="utf-8")
            context = ExecutionContext(Limits(max_findings=1), root / "STOP")
            result = RepositoryPostureCheck().run(Target(TargetKind.PATH, str(root)), context)
            self.assertEqual(result.status, "truncated")
            self.assertEqual(len(result.findings), 1)

    def _run(self, root: Path):
        return RepositoryPostureCheck().run(
            Target(TargetKind.PATH, str(root)), ExecutionContext(Limits(), root / "STOP")
        )


if __name__ == "__main__":
    unittest.main()
