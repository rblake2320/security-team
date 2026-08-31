from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
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

    def test_missing_static_assets_never_fall_back_to_the_spa_shell(self) -> None:
        self.assertFalse(server.allows_spa_fallback("assets/index.js.map"))
        self.assertFalse(server.allows_spa_fallback("security.txt"))
        self.assertFalse(server.allows_spa_fallback("evidence"))
        self.assertTrue(server.allows_spa_fallback("index.html"))


class ShowcaseHTTPBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.dist = Path(self.temporary_directory.name) / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<!doctype html><title>AEGIS</title>", encoding="utf-8")
        control = server.MissionControl(PROGRAM_ROOT, self.dist, mode="demo")

        class QuietHandler(server.Handler):
            def log_message(self, fmt, *args):
                return

        QuietHandler.control = control
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.temporary_directory.cleanup()

    def request(self, method: str, path: str, *, body: str | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=2)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        result = response.status, dict(response.getheaders()), payload
        connection.close()
        return result

    def test_head_static_route_matches_get_without_a_body(self) -> None:
        get_status, get_headers, get_body = self.request("GET", "/")
        head_status, head_headers, head_body = self.request("HEAD", "/")
        self.assertEqual((get_status, head_status), (200, 200))
        self.assertEqual(head_body, b"")
        self.assertEqual(head_headers["Content-Length"], get_headers["Content-Length"])
        self.assertEqual(int(get_headers["Content-Length"]), len(get_body))
        self.assertEqual(head_headers["X-Frame-Options"], "DENY")

    def test_demo_exposes_only_health_and_snapshot_api_reads(self) -> None:
        for path in ("/api/runs", "/api/activity", "/api/stream", "/api/v1/dashboard"):
            with self.subTest(path=path):
                status, headers, _body = self.request("GET", path)
                self.assertEqual(status, 404)
                self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")

        self.assertEqual(self.request("GET", "/api/health")[0], 200)
        self.assertEqual(self.request("GET", "/api/snapshot")[0], 200)

    def test_unknown_extensionless_server_path_is_a_real_404(self) -> None:
        status, headers, body = self.request("GET", "/definitely-not-a-route")
        self.assertEqual(status, 404)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(body), {"error": "not found"})

    def test_demo_control_post_fails_before_gate_validation(self) -> None:
        status, _headers, _body = self.request(
            "POST",
            "/api/runs",
            body='{"gateId":"definitely-not-real","mode":"engineering"}',
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
