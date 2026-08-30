from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


MISSION_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = MISSION_ROOT.parent
sys.path.insert(0, str(MISSION_ROOT))

import server  # noqa: E402


class AuditLedgerTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            ledger = server.AuditLedger(path)
            ledger.append("test.one", "First record", value="alpha")
            ledger.append("test.two", "Second record", value="beta")
            self.assertTrue(ledger.verify()["ok"])

            text = path.read_text(encoding="utf-8").replace("First record", "Changed record")
            path.write_text(text, encoding="utf-8")
            self.assertFalse(ledger.verify()["ok"])


class MissionControlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.control = server.MissionControl(PROGRAM_ROOT)

    def test_snapshot_is_derived_from_authoritative_program_files(self) -> None:
        snapshot = self.control.snapshot(fresh=True)
        self.assertEqual(snapshot["program"]["currentState"], "PREREQUISITES_PENDING")
        self.assertEqual(snapshot["program"]["verified"], 2)
        self.assertEqual(snapshot["program"]["total"], 4)
        self.assertEqual(len(snapshot["teams"]), 7)
        self.assertGreaterEqual(snapshot["gates"]["engineeringCount"], 18)

    def test_arbitrary_gate_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "authoritative manifest"):
            self.control.start_run("operator-supplied-shell", "engineering")

    def test_assurance_path_requires_explicit_confirmation(self) -> None:
        with self.assertRaisesRegex(PermissionError, "explicit confirmation"):
            self.control.start_run("readiness", "assurance", confirmed=False)

    def test_non_loopback_bind_is_rejected(self) -> None:
        self.assertEqual(server.main(["--host", "0.0.0.0"]), 2)

    def test_demo_mode_is_redacted_and_server_side_read_only(self) -> None:
        demo = server.MissionControl(PROGRAM_ROOT, mode="demo")
        snapshot = demo.snapshot(fresh=True)
        self.assertEqual(snapshot["deployment"]["mode"], "demo")
        self.assertFalse(snapshot["deployment"]["controlsEnabled"])
        self.assertFalse(snapshot["deployment"]["streamingEnabled"])
        self.assertEqual(snapshot["repo"]["commit"], "PUBLIC")
        self.assertEqual(snapshot["runs"], [])
        self.assertEqual(snapshot["activity"], [])
        self.assertTrue(snapshot["agents"]["demo"])
        with self.assertRaisesRegex(PermissionError, "read-only"):
            demo.start_run("appsec-baseline", "engineering")

    def test_control_requests_are_rate_limited(self) -> None:
        control = server.MissionControl(PROGRAM_ROOT)
        identity = "test-rate-limit-identity"
        for _ in range(server.CONTROL_REQUESTS_PER_WINDOW):
            self.assertTrue(control.allow_control_request(identity))
        self.assertFalse(control.allow_control_request(identity))


if __name__ == "__main__":
    unittest.main()
