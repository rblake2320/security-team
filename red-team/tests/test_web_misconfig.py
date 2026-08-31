"""Tests run against a real local HTTP server, not mocks - this check's whole job is
parsing real response headers, and the header-name casing / CORS-reflection logic is
exactly the kind of thing a mock would let pass while quietly being wrong."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from aegis_rt.checks.base import ExecutionContext
from aegis_rt.checks.web_misconfig import WebMisconfigCheck
from aegis_rt.models import Limits, Target, TargetKind


def _make_server(headers_by_path: dict):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            spec = headers_by_path.get(self.path, headers_by_path.get("/", {}))
            self.send_response(spec.get("_status", 200))
            for name, value in spec.get("headers", []):
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass  # keep test output clean

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class WebMisconfigCheckTests(unittest.TestCase):
    def _context(self) -> ExecutionContext:
        return ExecutionContext(Limits(max_requests=10), Path("no-stop-file-here"))

    def _run(self, headers_by_path: dict):
        server = _make_server(headers_by_path)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            return WebMisconfigCheck().run(Target(TargetKind.URL, url), self._context())
        finally:
            server.shutdown()
            server.server_close()

    def test_cors_credential_reflection_is_flagged(self):
        class ReflectingHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                origin = self.headers.get("Origin")
                self.send_response(200)
                if origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), ReflectingHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = WebMisconfigCheck().run(Target(TargetKind.URL, url), self._context())
        finally:
            server.shutdown()
            server.server_close()
        cors_findings = [f for f in result.findings if "CORS" in f.title]
        self.assertEqual(len(cors_findings), 1)
        self.assertEqual(cors_findings[0].severity.value, "high")
        self.assertEqual(cors_findings[0].evidence["reflected_acao"], "https://aegis-cors-probe.invalid")

    def test_wildcard_cors_without_credentials_is_not_flagged(self):
        """A bare `*` with no credentials is intentionally public (e.g. a public CDN
        asset) and must NOT be reported - flagging it would be a false positive that
        erodes trust in every other finding this check produces."""
        class OpenHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), OpenHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = WebMisconfigCheck().run(Target(TargetKind.URL, url), self._context())
        finally:
            server.shutdown()
            server.server_close()
        cors_findings = [f for f in result.findings if "CORS" in f.title]
        self.assertEqual(cors_findings, [])

    def test_missing_cookie_attributes_are_flagged(self):
        result = self._run({
            "/": {"headers": [("Set-Cookie", "session=abc123; Path=/"), ("X-Frame-Options", "DENY")]},
        })
        cookie_findings = [f for f in result.findings if "Cookie" in f.title]
        self.assertEqual(len(cookie_findings), 1)
        self.assertEqual(
            set(cookie_findings[0].evidence["missing_attributes"]),
            {"secure", "httponly", "samesite"},
        )

    def test_fully_flagged_cookie_produces_no_finding(self):
        result = self._run({
            "/": {"headers": [
                ("Set-Cookie", "session=abc123; Secure; HttpOnly; SameSite=Strict"),
                ("X-Frame-Options", "DENY"),
            ]},
        })
        self.assertEqual([f for f in result.findings if "Cookie" in f.title], [])

    def test_non_session_cookie_does_not_require_httponly(self):
        result = self._run({
            "/": {"headers": [("Set-Cookie", "theme=dark; Secure; SameSite=Lax")]},
        })
        self.assertEqual([f for f in result.findings if "Cookie" in f.title], [])

    def test_missing_clickjacking_protection_is_flagged(self):
        result = self._run({"/": {"headers": []}})
        clickjacking = [f for f in result.findings if "clickjacking" in f.title.lower()]
        self.assertEqual(len(clickjacking), 1)
        self.assertEqual(clickjacking[0].severity.value, "medium")

    def test_frame_ancestors_csp_satisfies_clickjacking_check(self):
        result = self._run({
            "/": {"headers": [("Content-Security-Policy", "frame-ancestors 'self'")]},
        })
        self.assertEqual([f for f in result.findings if "clickjacking" in f.title.lower()], [])

    def test_non_html_response_does_not_get_clickjacking_finding(self):
        result = self._run({
            "/": {"headers": [("Content-Type", "application/json")]},
        })
        self.assertEqual([f for f in result.findings if "clickjacking" in f.title.lower()], [])

    def test_kill_switch_stops_scan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / "STOP"
            stop.touch()
            context = ExecutionContext(Limits(), stop)
            with self.assertRaises(InterruptedError):
                WebMisconfigCheck().run(Target(TargetKind.URL, "http://127.0.0.1:1/"), context)


if __name__ == "__main__":
    unittest.main()
