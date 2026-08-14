from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from .base import ExecutionContext


class SourceStaticCheck:
    check_id = "source.static"
    target_kinds = frozenset({TargetKind.PATH})
    description = "Offline source review for high-signal secret and unsafe-code patterns"
    active = False
    _max_file_bytes = 2_000_000
    _extensions: ClassVar[set[str]] = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".ps1",
        ".cs",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".yaml",
        ".yml",
        ".json",
        ".env",
    }
    _excluded_parts = frozenset({".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build"})
    _rules = (
        (
            "embedded-private-key",
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            Severity.CRITICAL,
            "Private key material appears embedded in source",
            "Remove the key, revoke/rotate it, and use an approved secret store.",
            "CWE-798",
        ),
        (
            "generic-secret-assignment",
            re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"),
            Severity.HIGH,
            "Possible hard-coded credential",
            "Move credentials to an approved secret store and rotate exposed values.",
            "CWE-798",
        ),
        (
            "python-shell-true",
            re.compile(r"subprocess\.(?:run|Popen|call|check_output)\([^\n]*shell\s*=\s*True"),
            Severity.HIGH,
            "Shell execution may allow command injection",
            "Use an argument vector with shell=False and strict input validation.",
            "CWE-78",
        ),
        (
            "python-dynamic-code",
            re.compile(r"(?<![A-Za-z0-9_])(?:eval|exec)\s*\("),
            Severity.MEDIUM,
            "Dynamic code execution primitive detected",
            "Replace dynamic evaluation with explicit parsing or a constrained dispatcher.",
            "CWE-95",
        ),
        (
            "unsafe-deserialization",
            re.compile(r"(?:pickle\.loads?\s*\(|yaml\.load\s*\()"),
            Severity.HIGH,
            "Potentially unsafe deserialization",
            "Use a safe data format and safe loader; never deserialize untrusted objects.",
            "CWE-502",
        ),
    )

    def run(self, target: Target, context: ExecutionContext) -> CheckResult:
        root = Path(target.value).expanduser().resolve()
        files = [root] if root.is_file() else root.rglob("*")
        findings: list[Finding] = []
        for path in files:
            context.assert_running()
            try:
                resolved_path = path.resolve(strict=True)
                if root.is_dir():
                    resolved_path.relative_to(root)
            except (OSError, ValueError):
                # A link or junction may not escape the exact authorized root.
                continue
            if not resolved_path.is_file() or (
                resolved_path.suffix.lower() not in self._extensions and resolved_path.name.lower() != ".env"
            ):
                continue
            if self._excluded_parts.intersection(resolved_path.parts):
                continue
            context.consume_file()
            try:
                if resolved_path.stat().st_size > self._max_file_bytes:
                    continue
                content = resolved_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            relative = str(resolved_path.relative_to(root)) if root.is_dir() else resolved_path.name
            for rule_id, pattern, severity, title, remediation, cwe in self._rules:
                for match in pattern.finditer(content):
                    if len(findings) >= context.limits.max_findings:
                        return CheckResult(
                            self.check_id,
                            target.value,
                            "truncated",
                            tuple(findings),
                            error="finding budget exhausted",
                        )
                    line = content.count("\n", 0, match.start()) + 1
                    findings.append(
                        Finding(
                            check_id=self.check_id,
                            severity=severity,
                            title=title,
                            target=target.value,
                            description=f"{rule_id} matched in {relative}:{line}",
                            remediation=remediation,
                            # Never retain the match: even a digest can enable guessing attacks.
                            evidence={"file": relative, "line": line, "rule_id": rule_id},
                            cwe=cwe,
                        )
                    )
        return CheckResult(self.check_id, target.value, "completed", tuple(findings))
