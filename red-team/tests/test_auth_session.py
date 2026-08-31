"""Real local-server tests, same rationale as test_web_misconfig.py: this check's job is
parsing real response bodies/cookies, and mocking that would hide exactly the kind of bug
that matters here (regex-signal logic, header parsing)."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from aegis_rt.checks.auth_session import AuthSessionHygieneCheck
from aegis_rt.checks.base import ExecutionContext
from aegis_rt.models import Limits, Target, TargetKind


def _serve(handler_cls):
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _context() -> ExecutionContext:
    return ExecutionContext(Limits(max_requests=10), Path("no-stop-file-here"))


class AuthSessionHygieneCheckTests(unittest.TestCase):
    def test_unauthenticated_200_with_real_content_is_flagged_info(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<html><body>Welcome to the admin dashboard</body></html>")

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        unauth = [f for f in result.findings if "no credentials" in f.title.lower()]
        self.assertEqual(len(unauth), 1)
        self.assertEqual(unauth[0].severity.value, "info")

    def test_login_page_content_is_not_flagged(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<html><body>Please sign in to continue</body></html>")

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual([f for f in result.findings if "no credentials" in f.title.lower()], [])

    def test_401_status_is_not_flagged(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.end_headers()

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result.findings, ())

    def test_short_numeric_session_cookie_is_flagged(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.send_header("Set-Cookie", "sessionid=1234567; Path=/")
                self.end_headers()

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        weak = [f for f in result.findings if "weak-token" in f.title]
        self.assertEqual(len(weak), 1)
        self.assertIn("purely numeric", weak[0].evidence["signals"])
        self.assertIn("short (7 chars)", weak[0].evidence["signals"])

    def test_long_random_session_cookie_is_not_flagged(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.send_header(
                    "Set-Cookie",
                    "sessionid=9f3a7c1e2b8d4f60a1c3e5b7d9f1a3c5e7b9d1f3a5c7e9b1; Path=/",
                )
                self.end_headers()

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual([f for f in result.findings if "weak-token" in f.title], [])

    def test_non_session_cookie_is_ignored(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.send_header("Set-Cookie", "theme=dark; Path=/")
                self.end_headers()

            def log_message(self, *a):
                pass

        server = _serve(Handler)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = AuthSessionHygieneCheck().run(Target(TargetKind.URL, url), _context())
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result.findings, ())

    def test_kill_switch_stops_scan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / "STOP"
            stop.touch()
            context = ExecutionContext(Limits(), stop)
            with self.assertRaises(InterruptedError):
                AuthSessionHygieneCheck().run(Target(TargetKind.URL, "http://127.0.0.1:1/"), context)


if __name__ == "__main__":
    unittest.main()
