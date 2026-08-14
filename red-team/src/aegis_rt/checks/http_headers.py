from __future__ import annotations

import http.client
import socket
import ssl
from typing import ClassVar
from urllib.parse import urlsplit

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from ..scope import ScopeError, is_public_address, resolve_url_target
from .base import ExecutionContext


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout, self.source_address)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self) -> None:
        raw = socket.create_connection((self._address, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


class HttpHeadersCheck:
    check_id = "http.security_headers"
    target_kinds = frozenset({TargetKind.URL})
    description = "Pinned-address HEAD request with TLS verification and redirect suppression"
    active = True
    _headers: ClassVar[dict[str, tuple[Severity, str]]] = {
        "content-security-policy": (Severity.HIGH, "Define a restrictive Content-Security-Policy."),
        "strict-transport-security": (Severity.MEDIUM, "Enable HSTS after confirming HTTPS-only operation."),
        "x-content-type-options": (Severity.LOW, "Set X-Content-Type-Options: nosniff."),
        "referrer-policy": (Severity.LOW, "Set a restrictive Referrer-Policy."),
        "permissions-policy": (Severity.LOW, "Set a least-privilege Permissions-Policy."),
    }

    def run(self, target: Target, context: ExecutionContext) -> CheckResult:
        parsed = urlsplit(target.value)
        hostname, port, addresses = resolve_url_target(target.value)
        public = [address for address in addresses if is_public_address(address)]
        if public and not context.allow_public_targets:
            # Re-check immediately before connecting to close DNS rebinding races.
            raise ScopeError("target resolved out of approved scope during execution")
        address = addresses[0]  # Pinned after scope validation; prevents DNS rebinding mid-request.
        context.consume_request()
        connection_type = _PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection
        connection = connection_type(hostname, address, port, context.limits.timeout_seconds)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        rendered_host = f"[{hostname}]" if ":" in hostname else hostname
        host_header = rendered_host if parsed.port is None else f"{rendered_host}:{port}"
        try:
            connection.request(
                "HEAD",
                path,
                headers={"Host": host_header, "User-Agent": "Aegis-RT/0.1 authorized-assessment"},
            )
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            findings: list[Finding] = []
            for name, (severity, remediation) in self._headers.items():
                if name not in headers:
                    if name == "strict-transport-security" and parsed.scheme != "https":
                        continue
                    findings.append(
                        Finding(
                            check_id=self.check_id,
                            severity=severity,
                            title=f"Missing {name} response header",
                            target=target.value,
                            description=f"The HTTP response did not include {name}.",
                            remediation=remediation,
                            evidence={"status": response.status, "header": name},
                            cwe="CWE-693",
                        )
                    )
            if 300 <= response.status < 400:
                findings.append(
                    Finding(
                        check_id=self.check_id,
                        severity=Severity.INFO,
                        title="Redirect observed but not followed",
                        target=target.value,
                        description="Redirects are intentionally not followed to preserve approved scope.",
                        remediation="Add the redirect destination as an explicit scoped target if needed.",
                        evidence={"status": response.status},
                    )
                )
            return CheckResult(self.check_id, target.value, "completed", tuple(findings))
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            return CheckResult(self.check_id, target.value, "failed", error=str(exc))
        finally:
            connection.close()
