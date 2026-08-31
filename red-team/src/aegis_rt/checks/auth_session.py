"""Bounded, non-exploiting authentication/session hygiene checks.

Two detectors, both single-request, read-only, and honestly scoped to what a single
observation can actually prove:

  * Unauthenticated-access observation: sends ONE request with no credentials, no cookies,
    no Authorization header, and reports what came back. It does NOT decide whether that
    target is supposed to require authentication - it has no way to know that - so every
    finding here is INFO severity, framed as a candidate for human triage, same posture
    `repository_posture.py`'s R1-style over-inclusive lint already takes in this program.
  * Session-identifier weak-heuristic: inspects whatever Set-Cookie the unauthenticated
    response already carries for signs a session token may be short or predictable
    (length, character-class narrowness, purely-sequential-looking digits). This is a
    SINGLE-SAMPLE heuristic, explicitly not a statistical entropy measurement - a real
    entropy analysis needs many samples across repeated logins, and repeatedly
    authenticating to collect them is exactly the kind of credential-touching, brute-force-
    adjacent activity this program's charter permanently excludes. The finding text says so
    plainly rather than implying more rigor than a single sample can support.

No login attempted, no credential guessed, no session forged, no endpoint enumerated beyond
what the engagement operator explicitly listed as a target.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from ..scope import resolve_url_target, select_scoped_address
from ._pinned_http import connection_for
from .base import ExecutionContext

_LOGIN_SIGNAL = re.compile(r"\b(log[\s-]?in|sign[\s-]?in|unauthorized|please authenticate)\b", re.I)
_SESSION_COOKIE_NAME = re.compile(r"(sess|token|auth|sid)", re.I)


class AuthSessionHygieneCheck:
    check_id = "auth.session_hygiene"
    target_kinds = frozenset({TargetKind.URL})
    description = "Unauthenticated-access observation and single-sample session-token heuristic"
    active = True

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
        try:
            connection.request(
                "GET", path,
                headers={"Host": hostname, "User-Agent": "Aegis-RT/0.1 authorized-assessment"},
            )
            response = connection.getresponse()
            body = response.read(65_536)
            headers = [(key.lower(), value) for key, value in response.getheaders()]
        except Exception as exc:
            return CheckResult(self.check_id, target.value, "failed", error=str(exc))
        finally:
            connection.close()

        findings: list[Finding] = []
        findings.extend(self._unauth_findings(target.value, response.status, body))
        findings.extend(self._session_findings(target.value, headers))
        return CheckResult(self.check_id, target.value, "completed", tuple(findings))

    def _unauth_findings(self, target_value: str, status: int, body: bytes) -> list[Finding]:
        if status != 200:
            return []
        text = body.decode("utf-8", errors="replace")
        looks_like_login = bool(_LOGIN_SIGNAL.search(text))
        if looks_like_login:
            return []
        return [Finding(
            check_id=self.check_id,
            severity=Severity.INFO,
            title="Endpoint returned 200 with no credentials supplied",
            target=target_value,
            description=(
                "An unauthenticated GET returned HTTP 200 with a body that does not look "
                "like a login/auth-required page. This is a candidate for triage, not a "
                "confirmed finding - confirm whether this endpoint is intentionally public."
            ),
            remediation="If this endpoint should require authentication, enforce it server-side "
                        "and confirm with an authenticated-vs-unauthenticated response diff.",
            evidence={"status": status, "body_bytes": len(body)},
            cwe="CWE-306",
        )]

    def _session_findings(self, target_value: str, headers: list[tuple[str, str]]) -> list[Finding]:
        findings: list[Finding] = []
        for name, value in headers:
            if name != "set-cookie":
                continue
            cookie_name = value.split("=", 1)[0].strip()
            if not _SESSION_COOKIE_NAME.search(cookie_name):
                continue
            token = value.split("=", 1)[1].split(";", 1)[0].strip() if "=" in value else ""
            if not token:
                continue
            weak_reasons = self._weakness_signals(token)
            if weak_reasons:
                findings.append(Finding(
                    check_id=self.check_id,
                    severity=Severity.LOW,
                    title=f"Cookie '{cookie_name}' shows possible weak-token signals",
                    target=target_value,
                    description=(
                        f"Single-sample heuristic on '{cookie_name}' (not a statistical entropy "
                        f"measurement - one sample cannot prove predictability): {', '.join(weak_reasons)}."
                    ),
                    remediation="Generate session identifiers with a CSPRNG, at least 128 bits, "
                                "and confirm with a proper multi-sample entropy analysis if this "
                                "signal warrants it.",
                    evidence={"cookie_name": cookie_name, "token_length": len(token),
                              "signals": weak_reasons},
                    cwe="CWE-330",
                ))
        return findings

    @staticmethod
    def _weakness_signals(token: str) -> list[str]:
        reasons = []
        if len(token) < 16:
            reasons.append(f"short ({len(token)} chars)")
        if token.isdigit():
            reasons.append("purely numeric")
        distinct = len(set(token.lower()))
        if len(token) >= 8 and distinct <= 4:
            reasons.append(f"narrow character set ({distinct} distinct characters)")
        return reasons
