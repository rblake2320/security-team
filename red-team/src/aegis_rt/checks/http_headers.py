from __future__ import annotations

import http.client
import ssl
from typing import ClassVar
from urllib.parse import urlsplit

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from ..scope import resolve_url_target, select_scoped_address
from ._pinned_http import connection_for
from .base import ExecutionContext


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
        address = select_scoped_address(
            addresses,
            allow_public_targets=context.allow_public_targets,
        )
        context.consume_request()
        connection = connection_for(parsed.scheme, hostname, address, port, context.limits.timeout_seconds)
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
