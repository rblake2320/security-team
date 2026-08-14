from __future__ import annotations

import re
from pathlib import Path

from ..models import CheckResult, Finding, Severity, Target, TargetKind
from .base import ExecutionContext
from .safe_scan import read_verified, walk_scope, within_root


class RepositoryPostureCheck:
    """Bounded offline checks for dependency and CI trust-boundary weaknesses."""

    check_id = "repository.posture"
    target_kinds = frozenset({TargetKind.PATH})
    description = "Offline repository supply-chain and workflow-permission posture"
    active = False
    _max_file_bytes = 1_000_000

    def run(self, target: Target, context: ExecutionContext) -> CheckResult:
        root = Path(target.value).expanduser().resolve(strict=True)
        if not root.is_dir():
            return CheckResult(self.check_id, target.value, "not_applicable")
        findings: list[Finding] = []
        # RESIDUAL-HIGH: see safe_scan. Same check/use gap as the source scanner -
        # resolve, validate containment, then stat and read the path again.
        for path, expected in walk_scope(root):
            context.assert_running()
            if not within_root(path, root):
                continue
            relative = path.relative_to(root).as_posix()
            relevant = (
                path.name.startswith("requirements") and path.suffix == ".txt"
            ) or path.name == "pyproject.toml" or (
                relative.startswith(".github/workflows/") and path.suffix in {".yml", ".yaml"}
            )
            if not relevant:
                continue
            context.consume_file()
            content = read_verified(path, expected, max_bytes=self._max_file_bytes)
            if content is None:
                continue
            if path.name.startswith("requirements"):
                for number, line in enumerate(content.splitlines(), 1):
                    value = line.strip()
                    if value and not value.startswith(("#", "-")) and "==" not in value:
                        findings.append(self._finding(
                            target.value, relative, number, "unpinned-dependency", Severity.HIGH,
                            "Dependency is not exactly pinned", "Pin and hash-lock the reviewed artifact.",
                        ))
                        if len(findings) >= context.limits.max_findings:
                            return CheckResult(
                                self.check_id,
                                target.value,
                                "truncated",
                                tuple(findings),
                                "finding budget exhausted",
                            )
            elif path.name == "pyproject.toml":
                for match in re.finditer(r'(?m)^dependencies\s*=.*(?:>=|~=|\*=)', content):
                    findings.append(self._finding(
                        target.value, relative, content.count("\n", 0, match.start()) + 1,
                        "broad-project-dependency", Severity.HIGH,
                        "Project dependency permits unreviewed versions", "Use an exact reviewed runtime version.",
                    ))
            elif re.search(r"(?m)^\s*permissions\s*:\s*write-all\s*(?:#.*)?$", content):
                findings.append(self._finding(
                    target.value, relative, 1, "workflow-write-all", Severity.CRITICAL,
                    "Workflow grants write-all permissions", "Declare the minimum read/write permissions per job.",
                ))
            if len(findings) >= context.limits.max_findings:
                return CheckResult(self.check_id, target.value, "truncated", tuple(findings), "finding budget exhausted")
        return CheckResult(self.check_id, target.value, "completed", tuple(findings))

    def _finding(
        self, target: str, file: str, line: int, rule: str, severity: Severity, title: str, remediation: str
    ) -> Finding:
        return Finding(
            check_id=self.check_id,
            severity=severity,
            title=title,
            target=target,
            description=f"{rule} matched in {file}:{line}",
            remediation=remediation,
            evidence={"file": file, "line": line, "rule_id": rule},
            cwe="CWE-1104",
            attack="T1195.002",
        )
