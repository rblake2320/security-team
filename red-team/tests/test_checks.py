import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aegis_rt.checks.base import ExecutionContext
from aegis_rt.checks.http_headers import HttpHeadersCheck
from aegis_rt.checks.source import SourceStaticCheck
from aegis_rt.models import Limits, Target, TargetKind
from aegis_rt.scope import ScopeError


class CheckTests(unittest.TestCase):
    def test_source_finding_never_retains_secret_or_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = "super-secret-value-12345"
            (root / ".env").write_text(f'API_KEY="{secret}"\n', encoding="utf-8")
            context = ExecutionContext(Limits(), root / "STOP")
            result = SourceStaticCheck().run(Target(TargetKind.PATH, str(root)), context)
            encoded = str(result.to_dict())
            self.assertEqual(1, len(result.findings))
            self.assertNotIn(secret, encoded)
            self.assertNotIn("sha256", encoded.lower())

    def test_kill_switch_stops_offline_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.py").write_text("eval(user_input)", encoding="utf-8")
            stop = root / "STOP"
            stop.touch()
            context = ExecutionContext(Limits(), stop)
            with self.assertRaises(InterruptedError):
                SourceStaticCheck().run(Target(TargetKind.PATH, str(root)), context)

    @patch("aegis_rt.checks.http_headers.resolve_url_target")
    def test_dns_rebinding_to_public_is_blocked_at_execution(self, resolve):
        resolve.return_value = ("example.test", 80, ("93.184.216.34",))
        context = ExecutionContext(Limits(), Path("missing-stop"), allow_public_targets=False)
        with self.assertRaisesRegex(ScopeError, "out of approved scope"):
            HttpHeadersCheck().run(Target(TargetKind.URL, "http://example.test"), context)

    def test_source_link_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            outside_dir = base / "outside"
            outside_dir.mkdir()
            outside = outside_dir / "outside.py"
            outside.write_text("eval(sensitive)", encoding="utf-8")
            if os.name == "nt":
                link = root / "linked"
                completed = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside_dir)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                self.assertTrue(link.is_dir())
            else:
                link = root / "linked.py"
                link.symlink_to(outside)
            context = ExecutionContext(Limits(), base / "STOP")
            result = SourceStaticCheck().run(Target(TargetKind.PATH, str(root)), context)
            self.assertEqual(0, len(result.findings))
            self.assertEqual(0, context.files_used)


if __name__ == "__main__":
    unittest.main()
