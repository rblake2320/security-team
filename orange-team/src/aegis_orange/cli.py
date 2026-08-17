from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .errors import OrangeError
from .review import AttackPath, DesignReview, Recommendation, SafeTest
from .scoring import load_scorecard, score_review
from .stride import APPLICABLE, CATEGORIES, VIOLATES, Element, coverage

DEFAULT_SCORECARD = Path(__file__).resolve().parents[3] / "config" / "scorecard.json"


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _load(path: str | None) -> Any:  # noqa: ANN401
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def _elements(doc: dict[str, Any]) -> list[Element]:
    return [
        Element.create(
            e["element_id"], e["name"], e["element_type"],
            crosses_trust_boundary=bool(e.get("crosses_trust_boundary", False)),
        )
        for e in doc.get("elements", [])
    ]


def _review(doc: dict[str, Any]) -> DesignReview:
    return DesignReview(
        review_id=doc.get("review_id", "review"),
        found_paths=[AttackPath.create(**p) for p in doc.get("found_paths", [])],
        seeded_paths=[AttackPath.create(**dict(p, seeded=True)) for p in doc.get("seeded_paths", [])],
        recommendations=[Recommendation.create(**r) for r in doc.get("recommendations", [])],
        tests=[SafeTest.create(**t) for t in doc.get("tests", [])],
        knowledge_transfer=list(doc.get("knowledge_transfer", [])),
    )


def cmd_stride_matrix(_: argparse.Namespace) -> int:
    _emit({
        "categories": {c: VIOLATES[c] for c in CATEGORIES},
        "applicable_by_element_type": {k: list(v) for k, v in APPLICABLE.items()},
    })
    return 0


def cmd_stride_coverage(args: argparse.Namespace) -> int:
    doc = _load(args.model) or {}
    result = coverage(_elements(doc), doc.get("stride_considered", {}))
    _emit(result)
    return 0 if not result["trust_boundary_gaps"] else 1


def cmd_findings(args: argparse.Namespace) -> int:
    review = _review(_load(args.review) or {})
    _emit({
        "found_paths": [p.to_payload() for p in review.found_paths],
        "missed_seeded": review.missed_seeded(),
        "missed_seeded_critical": review.missed_seeded(severity="critical"),
        "automatic_failures": review.automatic_failures(),
    })
    return 0 if not review.automatic_failures() else 1


def cmd_score(args: argparse.Namespace) -> int:
    doc = _load(args.review) or {}
    review = _review(doc)
    model = _load(args.model) or {}
    result = score_review(
        review,
        load_scorecard(args.scorecard),
        elements=_elements(model) if model else None,
        stride_considered=model.get("stride_considered") if model else None,
    )
    _emit(result.to_payload())
    return 0 if result.status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-orange",
        description="Adversarial design review: STRIDE coverage, attack paths, safe test conversion",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stride-matrix", help="print the STRIDE-per-element applicability matrix").set_defaults(
        func=cmd_stride_matrix
    )

    c = sub.add_parser("stride-coverage", help="score STRIDE coverage of a design model")
    c.add_argument("--model", required=True)
    c.set_defaults(func=cmd_stride_coverage)

    f = sub.add_parser("findings", help="report discovered vs seeded paths")
    f.add_argument("--review", required=True)
    f.set_defaults(func=cmd_findings)

    s = sub.add_parser("score", help="compute S_O")
    s.add_argument("--review", required=True)
    s.add_argument("--model", help="design model, to report STRIDE coverage alongside discovery")
    s.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    s.set_defaults(func=cmd_score)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except OrangeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
