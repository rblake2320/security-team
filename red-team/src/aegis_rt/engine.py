from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .audit import AuditLedger
from .authorization import verify_authorization
from .checks import BUILTIN_CHECKS
from .checks.base import ExecutionContext
from .models import CheckResult, Engagement
from .scope import scope_fingerprint, validate_engagement


@dataclass(frozen=True)
class RunSummary:
    engagement_id: str
    scope_sha256: str
    results: tuple[CheckResult, ...]
    requests_used: int
    files_used: int

    @property
    def findings_count(self) -> int:
        return sum(len(result.findings) for result in self.results)


def build_plan(engagement: Engagement) -> list[tuple[object, object]]:
    unknown = sorted(set(engagement.allowed_checks) - set(BUILTIN_CHECKS))
    if unknown:
        raise ValueError("unknown checks: " + ", ".join(unknown))
    plan = []
    for target in engagement.targets:
        for check_id in engagement.allowed_checks:
            check = BUILTIN_CHECKS[check_id]
            if target.kind in check.target_kinds:
                plan.append((check, target))
    return plan


def run_engagement(
    engagement: Engagement,
    state_dir: Path,
    trusted_public_key: Path,
    require_authorization: bool = True,
) -> RunSummary:
    validate_engagement(engagement, require_authorization=require_authorization)
    if require_authorization:
        if engagement.authorization is None:
            raise ValueError("authorization receipt is required")
        verify_authorization(engagement.authorization, trusted_public_key)
    plan = build_plan(engagement)
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger = AuditLedger(state_dir / "audit.jsonl")
    context = ExecutionContext(
        engagement.limits,
        state_dir / "STOP",
        allow_public_targets=bool(engagement.authorization and engagement.authorization.allow_public_targets),
    )
    fingerprint = scope_fingerprint(engagement)
    ledger.append(
        "engagement.started",
        {"engagement_id": engagement.engagement_id, "scope_sha256": fingerprint, "tasks": len(plan)},
    )
    results: list[CheckResult] = []
    with ThreadPoolExecutor(max_workers=engagement.limits.max_concurrency) as pool:
        futures = {pool.submit(check.run, target, context): (check, target) for check, target in plan}
        for future in as_completed(futures):
            check, target = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # isolate plugin failures without hiding them
                result = CheckResult(check.check_id, target.value, "failed", error=str(exc))
            results.append(result)
            ledger.append(
                "check.finished",
                {
                    "check_id": result.check_id,
                    "target": result.target,
                    "status": result.status,
                    "findings": len(result.findings),
                    "error": result.error,
                },
            )
    results.sort(key=lambda item: (item.target, item.check_id))
    summary = RunSummary(
        engagement.engagement_id,
        fingerprint,
        tuple(results),
        context.requests_used,
        context.files_used,
    )
    ledger.append(
        "engagement.finished",
        {
            "findings": summary.findings_count,
            "requests_used": summary.requests_used,
            "files_used": summary.files_used,
        },
    )
    return summary
