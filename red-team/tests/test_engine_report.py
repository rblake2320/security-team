import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegis_rt.authorization import generate_keypair, sign_authorization
from aegis_rt.engine import run_engagement
from aegis_rt.models import Authorization, Engagement, Limits, Target, TargetKind
from aegis_rt.report import write_reports
from aegis_rt.scope import scope_fingerprint


class EngineReportTests(unittest.TestCase):
    def test_end_to_end_offline_run_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "app.py").write_text("eval(request)", encoding="utf-8")
            engagement = Engagement(
                "offline-1",
                "owner",
                (Target(TargetKind.PATH, str(source)),),
                ("source.static",),
                Limits(max_concurrency=1),
            )
            auth = Authorization(
                "approver",
                "SEC-2",
                (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                scope_fingerprint(engagement),
                "",
            )
            private_key = root / "issuer.pem"
            public_key = root / "issuer.pub.pem"
            password = b"a-long-test-password"
            generate_keypair(private_key, public_key, password)
            auth = replace(
                auth,
                signature=sign_authorization(auth, private_key, password),
            )
            engagement = replace(engagement, authorization=auth)
            summary = run_engagement(engagement, root / "state", public_key)
            self.assertEqual(1, summary.findings_count)
            self.assertEqual(1, summary.files_used)
            self.assertTrue((root / "state" / "audit.jsonl").exists())
            json_path, markdown_path = write_reports(summary, root / "reports")
            self.assertTrue(json_path.exists())
            self.assertIn("Dynamic code execution", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
