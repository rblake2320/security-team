from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .coverage import Asset, DefensibilityModel, TechniqueControl
from .errors import GreenError
from .scoring import load_scorecard, score_defensibility
from .telemetry import DataSource, inventory_summary

# parents[2] is the team directory (src/<pkg>/cli.py -> <team>-team). parents[3]
# would be the repository root, where no scorecard lives.
DEFAULT_SCORECARD = Path(__file__).resolve().parents[2] / "config" / "scorecard.json"


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _load(path: str | None) -> Any:  # noqa: ANN401
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def _model(args: argparse.Namespace) -> DefensibilityModel:
    """Build the model from a single environment document.

    One document rather than several files: assets, telemetry and techniques only
    mean anything together, and splitting them invites the three to drift.
    """
    doc = _load(args.environment) or {}
    assets = [Asset.create(a["asset_id"], a["name"], a["criticality"]) for a in doc.get("assets", [])]
    sources = [
        DataSource.create(s["name"], s["scores"], s["applies_to"])
        for s in doc.get("data_sources", [])
    ]
    techniques = [
        TechniqueControl.create(
            t["technique"], t["handling"],
            must_detect=bool(t.get("must_detect", False)),
            evidence=t.get("evidence", ""),
        )
        for t in doc.get("techniques", [])
    ]
    return DefensibilityModel(assets, sources, techniques)


def cmd_telemetry(args: argparse.Namespace) -> int:
    model = _model(args)
    _emit({
        "inventory": inventory_summary(model.sources),
        "sources": [s.to_payload() for s in model.sources],
    })
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    model = _model(args)
    _emit({
        "all_assets": model.telemetry_coverage(),
        "critical_assets": model.telemetry_coverage("critical"),
        "must_detect": model.must_detect_status(),
        "detection_effectiveness": round(model.detection_effectiveness(), 4),
        "automatic_failures": model.automatic_failures(),
    })
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    """Actionable gap list — what to fix, not just a percentage."""
    model = _model(args)
    critical = model.telemetry_coverage("critical")
    must = model.must_detect_status()
    _emit({
        "uncovered_critical_assets": critical["uncovered"],
        "unhandled_must_detect_techniques": must["unhandled"],
        "sources_below_quality_floor": inventory_summary(model.sources)["blind_sources"],
    })
    return 0 if not model.automatic_failures() else 1


def cmd_score(args: argparse.Namespace) -> int:
    model = _model(args)
    result = score_defensibility(
        model,
        load_scorecard(args.scorecard),
        hardening_results=_load(args.hardening),
        response_capabilities=_load(args.response),
        lifecycle_stages=_load(args.lifecycle),
    )
    _emit(result.to_payload())
    return 0 if result.status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-green",
        description="Defensive engineering: telemetry quality, ATT&CK coverage, defensibility scoring",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def with_env(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--environment", required=True, help="environment JSON document")
        return p

    with_env(sub.add_parser("telemetry", help="score telemetry data quality (DeTT&CT)")).set_defaults(
        func=cmd_telemetry
    )
    with_env(sub.add_parser("coverage", help="report asset and technique coverage")).set_defaults(
        func=cmd_coverage
    )
    with_env(sub.add_parser("gaps", help="list actionable gaps; non-zero exit if any auto-failure")).set_defaults(
        func=cmd_gaps
    )

    sc = with_env(sub.add_parser("score", help="compute S_G"))
    sc.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    sc.add_argument("--hardening")
    sc.add_argument("--response")
    sc.add_argument("--lifecycle")
    sc.set_defaults(func=cmd_score)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except GreenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
