from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .engine import RunSummary


def write_reports(summary: RunSummary, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "engagement_id": summary.engagement_id,
        "scope_sha256": summary.scope_sha256,
        "requests_used": summary.requests_used,
        "files_used": summary.files_used,
        "results": [result.to_dict() for result in summary.results],
    }
    json_path = output_dir / "findings.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    findings = [finding for result in summary.results for finding in result.findings]
    counts = Counter(finding.severity.value for finding in findings)
    lines = [
        f"# Aegis assessment: {summary.engagement_id}",
        "",
        f"Scope fingerprint: `{summary.scope_sha256}`",
        f"Requests used: {summary.requests_used}",
        f"Files inspected: {summary.files_used}",
        f"Findings: {len(findings)}",
        "",
        "## Severity summary",
        "",
        "| Critical | High | Medium | Low | Info |",
        "|---:|---:|---:|---:|---:|",
        f"| {counts['critical']} | {counts['high']} | {counts['medium']} | {counts['low']} | {counts['info']} |",
        "",
        "## Findings",
        "",
    ]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    for finding in sorted(findings, key=lambda item: (severity_order[item.severity.value], item.title)):
        lines.extend(
            [
                f"### [{finding.severity.value.upper()}] {_markdown(finding.title)}",
                "",
                f"- Target: `{_code(finding.target)}`",
                f"- Check: `{finding.check_id}`",
                f"- CWE: `{finding.cwe or 'n/a'}`",
                f"- Detail: {_markdown(finding.description)}",
                f"- Remediation: {_markdown(finding.remediation)}",
                "",
            ]
        )
    if not findings:
        lines.append("No findings were produced by the selected checks.")
    markdown_path = output_dir / "report.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def _markdown(value: str) -> str:
    return value.replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;").replace("\r", " ").replace("\n", " ")


def _code(value: str) -> str:
    return _markdown(value).replace("`", "\\`")
