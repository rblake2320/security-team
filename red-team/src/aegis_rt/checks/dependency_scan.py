"""Bounded, offline-to-the-target dependency vulnerability check.

Complements `repository.posture` (which flags dependencies that are UNPINNED) with a
different question: is the EXACT pinned version known-vulnerable? A repo can be 100%
pinned and still ship a version with a public CVE - pinning proves reproducibility, not
safety.

Delegates lookup to `pip-audit` (already a reviewed, hash-pinned CI dependency in this
program - see `tools/requirements-ci.txt`) rather than re-implementing a vulnerability
database. `pip-audit` is invoked once per discovered `requirements*.txt` file, reading
ONLY that file's text - it never inspects, imports, or executes anything from the target
repository's own code.

NOT fully offline, and that is disclosed here rather than implied by the `active = False`
flag: pip-audit queries a public third-party advisory service (PyPI's JSON API / OSV) to
resolve each package+version against known vulnerabilities. `active = False` is accurate
in this framework's sense - it means "makes no request to the TARGET" and is correctly
exempt from `ExecutionContext.consume_request()`'s target-request budget - but it is not
a zero-network check. If that distinction matters for a specific engagement's rules of
engagement, exclude this check_id from `allowed_checks`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from .base import ExecutionContext
from .safe_scan import read_verified, walk_scope, within_root

_TIMEOUT_SECONDS = 120
_MAX_FILE_BYTES = 200_000


class DependencyVulnerabilityCheck:
    """Audits pinned Python dependencies against public vulnerability advisories."""

    check_id = "dependency.vulnerability"
    target_kinds = frozenset({TargetKind.PATH})
    description = "Known-CVE audit of exactly-pinned Python requirements files"
    active = False

    def run(self, target: Target, context: ExecutionContext) -> CheckResult:
        root = Path(target.value).expanduser().resolve(strict=True)
        if not root.is_dir():
            return CheckResult(self.check_id, target.value, "not_applicable")

        findings: list[Finding] = []
        audited_any = False
        for path, expected in walk_scope(root):
            context.assert_running()
            if not within_root(path, root):
                continue
            if not (path.name.startswith("requirements") and path.suffix == ".txt"):
                continue
            context.consume_file()
            content = read_verified(path, expected, max_bytes=_MAX_FILE_BYTES)
            if content is None:
                continue
            relative = path.relative_to(root).as_posix()
            audited_any = True
            try:
                report = self._audit(content)
            except (subprocess.SubprocessError, OSError, ValueError, json.JSONDecodeError) as exc:
                findings.append(Finding(
                    check_id=self.check_id,
                    severity=Severity.INFO,
                    title="Dependency audit could not complete",
                    target=target.value,
                    description=f"{relative}: {type(exc).__name__} - advisory lookup failed or timed out",
                    remediation="Re-run once network access to the advisory service is available.",
                    evidence={"file": relative},
                ))
                continue
            for dep in report.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    findings.append(self._finding(target.value, relative, dep, vuln))
                    if len(findings) >= context.limits.max_findings:
                        return CheckResult(
                            self.check_id, target.value, "truncated",
                            tuple(findings), "finding budget exhausted",
                        )
        status = "completed" if audited_any else "not_applicable"
        return CheckResult(self.check_id, target.value, status, tuple(findings))

    def _audit(self, requirements_text: str) -> dict:
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(requirements_text)
            temp_path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip_audit", "-r", temp_path,
                 "--disable-pip", "--no-deps", "--format", "json", "--progress-spinner", "off"],
                capture_output=True, text=True, timeout=_TIMEOUT_SECONDS,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
        # pip-audit exits non-zero when it FINDS vulnerabilities, not only on error -
        # a naive check-returncode-first would silently drop every real finding.
        if not proc.stdout.strip():
            raise ValueError(f"pip-audit produced no output (stderr: {proc.stderr.strip()[:300]})")
        return json.loads(proc.stdout)

    def _finding(self, target: str, file: str, dep: dict, vuln: dict) -> Finding:
        name = dep.get("name", "unknown")
        version = dep.get("version", "unknown")
        vuln_id = vuln.get("id", "unknown")
        aliases = vuln.get("aliases") or []
        fix_versions = vuln.get("fix_versions") or []
        description = (vuln.get("description") or "").strip().splitlines()[0][:280]
        severity = Severity.HIGH if not fix_versions else Severity.MEDIUM
        remediation = (
            f"Upgrade {name} to {fix_versions[0]} or later." if fix_versions
            else f"No fixed version published yet for {vuln_id}; track the advisory."
        )
        return Finding(
            check_id=self.check_id,
            severity=severity,
            title=f"{name} {version} has a known vulnerability ({vuln_id})",
            target=target,
            description=description or f"{name} {version} matches {vuln_id}",
            remediation=remediation,
            evidence={
                "file": file,
                "package": name,
                "installed_version": version,
                "vulnerability_id": vuln_id,
                "aliases": aliases,
                "fix_versions": fix_versions,
            },
            cwe="CWE-1104",
        )
