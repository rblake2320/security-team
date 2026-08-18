#!/usr/bin/env python3
"""Program-level capability roll-up across the seven teams.

Every team scorecard publishes a `program_weight_7team`. The seven weights sum to
exactly 1.0. Until now nothing read them: seven scores existed and the program-level
number they were designed to produce had to be worked out by hand, which meant in
practice it was not worked out at all.

This implements the five rules the scorecards themselves publish, verbatim:

  1. Weights and thresholds are PUBLISHED BEFORE EXECUTION and FROZEN at execution
     start.  -> the weight set is verified to sum to 1.0 and its digest is recorded
     in the output, so a later weight change is detectable rather than silent.
  2. Automatic-failure conditions are evaluated BEFORE aggregation. Any auto-fail on
     ANY team sets program_status=FAILED; the weighted score is retained for
     diagnostics only.
  3. Evidence completeness is checked before a readiness band is assigned; below
     threshold yields INSUFFICIENT_EVIDENCE.
  4. A score of 95%+ triggers a MANDATORY challenge review, not a conclusion.
  5. Weights are governance defaults, revised only via versioned governance change.

It also refuses to launder a diagnostic number into an assurance statement: while
the program readiness gate is unmet, every result carries
TRAINING_OR_ENGINEERING_USE_ONLY and `assurance_permitted` is false.

Usage:
    python 00-shared/tools/program_rollup.py --scores <dir-of-team-score-json> [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROGRAM = Path(__file__).resolve().parents[2]
TEAMS = ("purple", "white", "yellow", "green", "orange", "blue", "red")
READINESS = PROGRAM / "00-shared" / "config" / "assessment_readiness.json"

# Rule 3: a team whose components are mostly undemonstrated has not produced enough
# evidence to band. Set at half: below this the score says more about what was not
# exercised than about the capability.
EVIDENCE_COMPLETENESS_FLOOR = 0.5

# Rule 4.
CHALLENGE_REVIEW_THRESHOLD = 0.95

WEIGHT_TOLERANCE = 1e-9


class RollupError(RuntimeError):
    """The roll-up cannot be computed as specified."""


def load_scorecards() -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for team in TEAMS:
        path = PROGRAM / f"{team}-team" / "config" / "scorecard.json"
        if not path.is_file():
            raise RollupError(f"missing scorecard for {team}: {path}")
        card = json.loads(path.read_text(encoding="utf-8"))
        if card.get("team") != team:
            raise RollupError(f"{path} declares team={card.get('team')!r}, expected {team!r}")
        if "program_weight_7team" not in card:
            raise RollupError(f"{team} scorecard publishes no program_weight_7team")
        cards[team] = card
    return cards


def weight_digest(cards: dict[str, dict[str, Any]]) -> str:
    """Digest of the frozen weight/threshold set (rule 1).

    Recorded in every result so that a governance change to the weights is visible
    when comparing two roll-ups, rather than silently reshaping history.
    """
    material = {
        team: {
            "program_weight_7team": cards[team]["program_weight_7team"],
            "pass_threshold": cards[team].get("pass_threshold"),
        }
        for team in TEAMS
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_weights(cards: dict[str, dict[str, Any]]) -> float:
    total = sum(float(cards[t]["program_weight_7team"]) for t in TEAMS)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise RollupError(
            f"published program weights sum to {total}, not 1.0 - the weight set is not "
            "internally consistent and no program score may be derived from it"
        )
    return total


def load_scores(scores_dir: Path) -> dict[str, dict[str, Any]]:
    """Load whatever team score documents are present.

    Absent teams are not an error: a partial assessment is a normal state. They are
    reported as not_assessed and excluded from the weighted mean with the remaining
    weights renormalized, exactly as an undemonstrated component is handled inside a
    single team.
    """
    found: dict[str, dict[str, Any]] = {}
    if not scores_dir.is_dir():
        raise RollupError(f"scores directory not found: {scores_dir}")
    for path in sorted(scores_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RollupError(f"{path.name} is not valid JSON: {exc}") from exc
        team = doc.get("team")
        if team not in TEAMS:
            raise RollupError(f"{path.name} declares unknown team {team!r}")
        if team in found:
            raise RollupError(f"two score documents for team {team!r}")
        found[team] = doc
    if not found:
        raise RollupError(f"no team score documents found in {scores_dir}")
    return found


def evidence_completeness(score: dict[str, Any]) -> float:
    components = score.get("components") or []
    if not components:
        return 0.0
    scored = [c for c in components if c.get("status") == "scored"]
    return len(scored) / len(components)


def rollup(cards: dict[str, dict[str, Any]], scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    verify_weights(cards)

    teams: list[dict[str, Any]] = []
    auto_failed: list[str] = []
    insufficient: list[str] = []
    contributing_weight = 0.0
    weighted_sum = 0.0

    for team in TEAMS:
        card = cards[team]
        weight = float(card["program_weight_7team"])
        score = scores.get(team)

        if score is None:
            teams.append({
                "team": team, "weight": weight, "state": "not_assessed",
                "score": None, "auto_failures": [], "evidence_completeness": None,
            })
            continue

        failures = list(score.get("auto_failures") or [])
        completeness = evidence_completeness(score)
        value = float(score.get("weighted_score", 0.0))

        # Rule 2: evaluated BEFORE aggregation.
        if failures:
            auto_failed.append(team)

        # Rule 3: checked before a band is assigned.
        state = "scored"
        if completeness < EVIDENCE_COMPLETENESS_FLOOR:
            state = "insufficient_evidence"
            insufficient.append(team)

        teams.append({
            "team": team,
            "weight": weight,
            "state": state,
            "score": round(value, 4),
            "team_status": score.get("status"),
            "auto_failures": failures,
            "evidence_completeness": round(completeness, 4),
        })

        # A team with insufficient evidence still contributes its auto-failures but
        # not its number: aggregating a score that is mostly "not demonstrated" would
        # manufacture confidence out of absence.
        if state == "scored":
            contributing_weight += weight
            weighted_sum += weight * value

    program_score = (weighted_sum / contributing_weight) if contributing_weight else 0.0
    coverage = contributing_weight  # weights sum to 1.0, so this is the covered fraction

    if auto_failed:
        status = "FAILED"
    elif not contributing_weight:
        status = "INSUFFICIENT_EVIDENCE"
    elif insufficient:
        status = "INSUFFICIENT_EVIDENCE"
    elif program_score >= CHALLENGE_REVIEW_THRESHOLD:
        # Rule 4: not a pass, not a conclusion.
        status = "CHALLENGE_REVIEW_REQUIRED"
    else:
        # There is no published program-level pass threshold, only per-team ones, so
        # the program band is deliberately descriptive rather than a verdict.
        status = "SCORED"

    notes: list[str] = []
    if auto_failed:
        notes.append(
            "rule 2: automatic failure on "
            + ", ".join(auto_failed)
            + " -> program_status=FAILED; the weighted score is diagnostic only"
        )
    if insufficient:
        notes.append(
            "rule 3: insufficient evidence from " + ", ".join(insufficient)
            + f" (below {EVIDENCE_COMPLETENESS_FLOOR:.0%} of components demonstrated); "
            "their scores are excluded from the weighted mean"
        )
    missing = [t["team"] for t in teams if t["state"] == "not_assessed"]
    if missing:
        notes.append(
            "not assessed: " + ", ".join(missing)
            + " -> remaining weights renormalized rather than assumed"
        )
    if status == "CHALLENGE_REVIEW_REQUIRED":
        notes.append(
            f"rule 4: {program_score:.1%} is at or above {CHALLENGE_REVIEW_THRESHOLD:.0%} and "
            "triggers a MANDATORY challenge review - a high score is a prompt to look harder, "
            "not a conclusion"
        )
    notes.append("rule 5: weights are governance defaults; revise only via versioned change")

    readiness = read_readiness()
    return {
        "schema": "program-rollup/1.0",
        "program_status": status,
        "program_score": round(program_score, 4),
        "coverage": round(coverage, 4),
        "weight_digest": weight_digest(cards),
        "readiness_state": readiness["state"],
        "assurance_permitted": readiness["assurance_permitted"],
        "marking": readiness["marking"],
        "auto_failed_teams": auto_failed,
        "insufficient_evidence_teams": insufficient,
        "teams": teams,
        "notes": notes,
    }


def read_readiness() -> dict[str, Any]:
    """Program readiness governs whether any of this may be called assurance."""
    if not READINESS.is_file():
        return {"state": "UNKNOWN", "assurance_permitted": False,
                "marking": "TRAINING_OR_ENGINEERING_USE_ONLY"}
    doc = json.loads(READINESS.read_text(encoding="utf-8"))
    state = doc.get("state_model", {}).get("current_state", "UNKNOWN")
    gates = doc.get("gate_definitions", {})
    required = doc.get("assessment_readiness", {}).get("required_gates", [])
    unmet = [g for g in required if gates.get(g, {}).get("status") != "VERIFIED"]
    permitted = not unmet and state == "ASSESSMENT_READY"
    on_failure = doc.get("assessment_readiness", {}).get("on_failure", {})
    return {
        "state": state,
        "assurance_permitted": bool(permitted),
        "marking": on_failure.get("result_marking", "TRAINING_OR_ENGINEERING_USE_ONLY")
        if not permitted else "ASSESSMENT",
        "unmet_gates": unmet,
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "PROGRAM CAPABILITY ROLL-UP - seven-team security model",
        "",
        f"  status            {result['program_status']}",
        f"  program score     {result['program_score']}   (coverage {result['coverage']:.0%} of program weight)",
        f"  readiness         {result['readiness_state']}",
        f"  assurance         {'PERMITTED' if result['assurance_permitted'] else 'PROHIBITED'}  [{result['marking']}]",
        f"  weight digest     {result['weight_digest'][:16]}...",
        "",
        f"  {'team':8} {'weight':>7} {'score':>7} {'evidence':>9}  state",
    ]
    for t in result["teams"]:
        score = "  n/a" if t["score"] is None else f"{t['score']:.3f}"
        ev = "  n/a" if t["evidence_completeness"] is None else f"{t['evidence_completeness']:.0%}"
        flag = "  AUTO-FAIL" if t["auto_failures"] else ""
        lines.append(f"  {t['team']:8} {t['weight']:>7} {score:>7} {ev:>9}  {t['state']}{flag}")
    lines.append("")
    for note in result["notes"]:
        lines.append(f"  - {note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Program-level capability roll-up")
    parser.add_argument("--scores", required=True, help="directory of per-team score JSON documents")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    try:
        cards = load_scorecards()
        scores = load_scores(Path(args.scores))
        result = rollup(cards, scores)
    except RollupError as exc:
        print(f"ROLL-UP ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True) if args.json else render(result))
    # FAILED must be non-zero so CI can gate on it. INSUFFICIENT_EVIDENCE is also
    # non-zero: "we did not look" must not read the same as "we looked and it was fine".
    return 0 if result["program_status"] in {"SCORED", "CHALLENGE_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
