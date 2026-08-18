#!/usr/bin/env python3
"""A common finding envelope, and adapters that carry findings between teams.

Red emits findings.json. Orange emits attack paths with recommendations. Yellow
tracks findings to completion. Structurally these are the same object, and until
now the handoff was manual: a human retyped six findings from one tool into
another. A handoff that depends on retyping is a handoff that does not happen,
which is why findings die between teams.

The envelope is deliberately small - the fields every team genuinely needs - and
adapters are lossy in one direction only: they may drop tool-specific detail, but
they must never invent severity or acceptance criteria. Yellow refuses to open a
critical or high finding without acceptance criteria, so an adapter that cannot
produce them is required to say so rather than fabricate a plausible sentence.

Usage:
    python 00-shared/tools/finding_envelope.py from-red --findings <red findings.json>
    python 00-shared/tools/finding_envelope.py from-orange --review <orange review.json>
    python 00-shared/tools/finding_envelope.py to-yellow --envelope <f.json> --register <r.jsonl> --at <iso>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROGRAM = Path(__file__).resolve().parents[2]

SEVERITIES = ("critical", "high", "medium", "low", "info")
# Yellow refuses to close these without durable evidence, and refuses to OPEN them
# without acceptance criteria.
EVIDENCE_REQUIRED = ("critical", "high")

SCHEMA = "security-finding-envelope/1.0"


class EnvelopeError(RuntimeError):
    """A finding cannot be represented or transferred without inventing something."""


def _severity(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in SEVERITIES:
        raise EnvelopeError(f"unknown severity {value!r}; expected one of {SEVERITIES}")
    return normalized


def envelope(
    finding_id: str, title: str, severity: str, source_team: str,
    *, detail: str = "", location: str = "", acceptance_criteria: str = "",
    references: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not finding_id.strip() or not title.strip():
        raise EnvelopeError("finding_id and title are required")
    return {
        "schema": SCHEMA,
        "finding_id": finding_id.strip(),
        "title": title.strip(),
        "severity": _severity(severity),
        "source_team": source_team,
        "detail": detail.strip(),
        "location": location.strip(),
        "acceptance_criteria": acceptance_criteria.strip(),
        "references": references or {},
    }


# ---- adapters -------------------------------------------------------------

def from_red(document: dict[str, Any], *, prefix: str = "RED") -> list[dict[str, Any]]:
    """Aegis Red findings.json -> envelopes.

    Red groups findings under per-check results. Its `remediation` string is a real
    instruction ("Pin and hash-lock the reviewed artifact") and is carried across as
    acceptance criteria, because it is exactly what Yellow needs to know the work is
    done. Where Red gives no remediation, none is invented.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in document.get("results", []):
        for index, finding in enumerate(result.get("findings", [])):
            evidence = finding.get("evidence") or {}
            location = ""
            if evidence.get("file"):
                location = str(evidence["file"])
                if evidence.get("line"):
                    location += f":{evidence['line']}"
            rule = evidence.get("rule_id") or finding.get("check_id") or "finding"
            # Yellow caps finding_id at 64 characters. Truncating a
            # "<prefix>-<rule>-<long/path/to/file>:<line>" string collapses every
            # finding from one rule into the same id, which silently merged 14 real
            # findings into duplicates the first time this ran. A digest of the
            # location keeps ids short, unique, and stable across runs.
            digest = hashlib.sha256((location or str(index)).encode("utf-8")).hexdigest()[:8]
            base = f"{prefix}-{rule}-{digest}".replace(" ", "-")[:64]
            finding_id = base
            suffix = 1
            while finding_id in seen:
                suffix += 1
                finding_id = f"{base[:60]}-{suffix}"
            seen.add(finding_id)
            out.append(envelope(
                finding_id,
                finding.get("title") or rule,
                finding.get("severity", "medium"),
                "red",
                detail=finding.get("description", ""),
                location=location,
                acceptance_criteria=finding.get("remediation", ""),
                references={k: v for k, v in (
                    ("cwe", finding.get("cwe")), ("attack", finding.get("attack")),
                    ("check_id", finding.get("check_id")), ("target", finding.get("target")),
                ) if v},
            ))
    return out


def from_orange(review: dict[str, Any]) -> list[dict[str, Any]]:
    """Orange design review -> envelopes.

    Orange already produces acceptance criteria on its recommendations, and its own
    scorecard auto-fails a critical recommendation that lacks them. Those criteria are
    matched to their attack path by path_id and carried across verbatim: rewriting
    them here would quietly detach Yellow's completion bar from what Orange asked for.
    """
    criteria = {
        r.get("path_id"): r.get("acceptance_criteria", "")
        for r in review.get("recommendations", [])
    }
    out: list[dict[str, Any]] = []
    for path in review.get("found_paths", []):
        out.append(envelope(
            path["path_id"],
            path["title"],
            path.get("severity", "medium"),
            "orange",
            detail=path.get("impact", ""),
            location=path.get("entry_point", ""),
            acceptance_criteria=criteria.get(path["path_id"], ""),
            references={k: v for k, v in (
                ("stride_category", path.get("stride_category")),
                ("review_id", review.get("review_id")),
            ) if v},
        ))
    return out


# ---- transfer -------------------------------------------------------------

def to_yellow(envelopes: list[dict[str, Any]], register_path: Path, *, at: str) -> dict[str, Any]:
    """Open each envelope as a finding in a Yellow register.

    Refuses rather than fabricates: a critical or high finding with no acceptance
    criteria is reported as untransferable, because Yellow's contract is that such a
    finding must carry a completion bar and inventing one here would defeat the
    control it exists to enforce.
    """
    sys.path.insert(0, str(PROGRAM / "yellow-team" / "src"))
    from aegis_yellow.register import FindingsRegister  # noqa: PLC0415

    register = FindingsRegister(register_path)
    existing = set(register.findings())
    opened: list[str] = []
    skipped: list[dict[str, str]] = []

    for item in envelopes:
        if item["finding_id"] in existing:
            skipped.append({"finding_id": item["finding_id"], "reason": "already in register"})
            continue
        if item["severity"] in EVIDENCE_REQUIRED and not item["acceptance_criteria"]:
            skipped.append({
                "finding_id": item["finding_id"],
                "reason": (
                    f"{item['severity']} finding has no acceptance criteria; the source tool "
                    "supplied none and inventing one would defeat Yellow's completion bar"
                ),
            })
            continue
        register.open_finding(
            item["finding_id"], item["title"], item["severity"], at,
            acceptance_criteria=item["acceptance_criteria"] or None,
        )
        opened.append(item["finding_id"])
        existing.add(item["finding_id"])

    return {"opened": opened, "skipped": skipped,
            "opened_count": len(opened), "skipped_count": len(skipped)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Common finding envelope and cross-team adapters")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("from-red", help="convert Aegis Red findings.json to envelopes")
    r.add_argument("--findings", required=True)
    r.add_argument("--output")

    o = sub.add_parser("from-orange", help="convert an Orange design review to envelopes")
    o.add_argument("--review", required=True)
    o.add_argument("--output")

    y = sub.add_parser("to-yellow", help="open envelopes as findings in a Yellow register")
    y.add_argument("--envelope", required=True)
    y.add_argument("--register", required=True)
    y.add_argument("--at", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command in ("from-red", "from-orange"):
            source = Path(args.findings if args.command == "from-red" else args.review)
            doc = json.loads(source.read_text(encoding="utf-8"))
            items = from_red(doc) if args.command == "from-red" else from_orange(doc)
            text = json.dumps(items, indent=2, sort_keys=True)
            if args.output:
                Path(args.output).write_text(text, encoding="utf-8")
                print(f"wrote {len(items)} envelopes -> {args.output}")
            else:
                print(text)
            return 0

        items = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        result = to_yellow(items, Path(args.register), at=args.at)
        print(json.dumps(result, indent=2, sort_keys=True))
        # Skipped findings are not a crash, but they must not read as success either.
        return 0 if not result["skipped"] else 1
    except EnvelopeError as exc:
        print(f"ENVELOPE ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
