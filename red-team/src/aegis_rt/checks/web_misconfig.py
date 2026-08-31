"""Bounded, non-exploiting web misconfiguration checks.

Three detectors, each a passive observation of what the server itself sends back - no
payload, no exploitation, matching this program's charter (`red-team/CHARTER.md`:
"deliberately excludes... destructive payloads"):

  * CORS reflected-origin-with-credentials: sends one extra request carrying a synthetic,
    clearly-fake Origin header and observes whether the server reflects it back with
    Access-Control-Allow-Credentials: true. That specific combination - not a bare
    wildcard - is the actual exploitable misconfiguration (RFC 6454 / OWASP CORS
    guidance); a wildcard ACAO *without* credentials is intentionally public and not
    flagged as a finding here.
  * Cookie hygiene: inspects Set-Cookie headers already present on the baseline response
    for missing Secure / HttpOnly / SameSite attributes. No second request.
  * Clickjacking: checks for a missing X-Frame-Options or CSP frame-ancestors directive.
    No second request.

NOT implemented, and deliberately so: open-redirect probing. This framework's own
`scope.resolve_url_target` rejects any URL target carrying a query string
("URL targets must not contain query strings or fragments") - there is no scope-compatible
way to attach a `?next=` / `?redirect=` probe parameter to a Target as currently modeled.
Adding it would require a deliberate extension to the Target/scope model, not a workaround
inside one check.
"""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlsplit

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from ..scope import resolve_url_target, select_scoped_address
from ._pinned_http import connection_for
from .base import ExecutionContext

_PROBE_ORIGIN = "https://aegis-cors-probe.invalid"
_SESSION_COOKIE_NAME = re.compile(r"(sess|token|auth|sid)", re.I)
_MAX_RESPONSE_BYTES = 65_536


class WebMisconfigCheck:
    check_id = "web.misconfig"
    target_kinds = frozenset({TargetKind.URL})
    description = "CORS credential reflection, cookie flag hygiene, and clickjacking header checks"
    active = True
    _cookie_attrs: ClassVar[tuple[str, ...]] = ("secure", "httponly", "samesite")

    def run(self, target: Target, context: ExecutionContext) -> CheckResult:
        parsed = urlsplit(target.value)
        hostname, port, addresses = resolve_url_target(target.value)
        address = select_scoped_address(
            addresses,
            allow_public_targets=context.allow_public_targets,
        )
        findings: list[Finding] = []

        baseline = self._get(target, context, parsed, hostname, address, port, origin=None)
        if baseline is None:
            return CheckResult(self.check_id, target.value, "failed", error="baseline request failed")
        status, headers = baseline
        findings.extend(self._cookie_findings(target.value, headers))
        findings.extend(self._clickjacking_findings(target.value, status, headers))

        cors_probe = self._get(target, context, parsed, hostname, address, port, origin=_PROBE_ORIGIN)
        if cors_probe is not None:
            _, cors_headers = cors_probe
            findings.extend(self._cors_findings(target.value, cors_headers))

        return CheckResult(self.check_id, target.value, "completed", tuple(findings))

    def _get(self, target, context, parsed, hostname, address, port, *, origin):
        context.consume_request()
        connection = connection_for(parsed.scheme, hostname, address, port, context.limits.timeout_seconds)
        path = parsed.path or "/"
        try:
            request_headers = {"Host": hostname, "User-Agent": "Aegis-RT/0.1 authorized-assessment"}
            if origin is not None:
                request_headers["Origin"] = origin
            connection.request("GET", path, headers=request_headers)
            response = connection.getresponse()
            response.read(_MAX_RESPONSE_BYTES + 1)
            headers = [(key.lower(), value) for key, value in response.getheaders()]
            return response.status, headers
        except Exception:
            return None
        finally:
            connection.close()

    def _cookie_findings(self, target_value: str, headers: list[tuple[str, str]]) -> list[Finding]:
        findings: list[Finding] = []
        for name, value in headers:
            if name != "set-cookie":
                continue
            lowered = value.lower()
            cookie_name = value.split("=", 1)[0].strip()
            if not _SESSION_COOKIE_NAME.search(cookie_name):
                continue
            missing = [attr for attr in self._cookie_attrs if attr not in lowered]
            if missing:
                findings.append(Finding(
                    check_id=self.check_id,
                    severity=Severity.MEDIUM,
                    title=f"Cookie '{cookie_name}' missing {', '.join(missing)}",
                    target=target_value,
                    description=(
                        f"Set-Cookie for '{cookie_name}' does not declare: {', '.join(missing)}."
                    ),
                    remediation="Set Secure, HttpOnly, and an explicit SameSite attribute on every cookie.",
                    evidence={"cookie_name": cookie_name, "missing_attributes": missing},
                    cwe="CWE-1004" if "httponly" in missing else "CWE-614",
                ))
        return findings

    def _clickjacking_findings(self, target_value: str, status: int, headers: list[tuple[str, str]]) -> list[Finding]:
        header_map = dict(headers)
        content_type = header_map.get("content-type", "").lower()
        if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return []
        has_xfo = "x-frame-options" in header_map
        csp = header_map.get("content-security-policy", "")
        has_frame_ancestors = "frame-ancestors" in csp.lower()
        if not has_xfo and not has_frame_ancestors and status < 400:
            return [Finding(
                check_id=self.check_id,
                severity=Severity.MEDIUM,
                title="No clickjacking protection (X-Frame-Options or frame-ancestors)",
                target=target_value,
                description="Response has neither X-Frame-Options nor a CSP frame-ancestors directive.",
                remediation="Set X-Frame-Options: DENY (or SAMEORIGIN) or a CSP frame-ancestors directive.",
                evidence={"status": status},
                cwe="CWE-1021",
            )]
        return []

    def _cors_findings(self, target_value: str, headers: list[tuple[str, str]]) -> list[Finding]:
        header_map = dict(headers)
        acao = header_map.get("access-control-allow-origin")
        acac = header_map.get("access-control-allow-credentials", "").lower()
        if acao == _PROBE_ORIGIN and acac == "true":
            return [Finding(
                check_id=self.check_id,
                severity=Severity.HIGH,
                title="CORS reflects an arbitrary Origin with credentials allowed",
                target=target_value,
                description=(
                    f"A synthetic, never-registered Origin ({_PROBE_ORIGIN}) was reflected back "
                    "in Access-Control-Allow-Origin alongside Access-Control-Allow-Credentials: true. "
                    "This lets ANY origin make credentialed cross-origin requests."
                ),
                remediation="Validate Origin against an explicit allow-list before reflecting it, "
                            "or drop Access-Control-Allow-Credentials if origins must stay open.",
                evidence={"probe_origin": _PROBE_ORIGIN, "reflected_acao": acao},
                cwe="CWE-942",
            )]
        return []
