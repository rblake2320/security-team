#!/usr/bin/env python3
"""Program capability history and drift.

Every score this program produces is a snapshot. For a capability programme the
operative question is not "what is the number" but "which direction is it moving,
and did anything regress while the headline improved". Nothing answered that,
because nothing was retained.

History is append-only and hash-chained for the same reason the team ledgers are:
a trend line that can be edited after the fact is a story, not evidence.

Two properties worth stating:

  * A roll-up is only comparable to another roll-up computed under the SAME weight
    set. The weight digest is recorded with each entry and a comparison across a
    governance weight change is reported as incomparable rather than silently
    plotted as movement.
  * Coverage is carried alongside the score. A score that "improves" while coverage
    falls is usually not improvement, it is a narrower question being asked.

Usage:
    python 00-shared/tools/program_history.py record --rollup <rollup.json> --history <file>
    python 00-shared/tools/program_history.py trend --history <file>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

GENESIS_PREV = "0" * 64


class HistoryError(RuntimeError):
    """History is unreadable, broken, or being asked an impossible question."""


def _entry_hash(prev_hash: str, sequence: int, payload: dict[str, Any]) -> str:
    material = json.dumps(
        {"prev": prev_hash, "seq": sequence, "payload": payload},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def read_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise HistoryError(f"history line {number} is not valid JSON: {exc}") from exc
    return entries


def verify_history(entries: list[dict[str, Any]]) -> int:
    expected_prev = GENESIS_PREV
    for index, entry in enumerate(entries):
        for field in ("sequence", "prev_hash", "entry_hash", "payload"):
            if field not in entry:
                raise HistoryError(f"history entry {index} is missing {field}")
        if entry["sequence"] != index:
            raise HistoryError(f"history entry {index} has sequence {entry['sequence']}")
        if entry["prev_hash"] != expected_prev:
            raise HistoryError(f"history entry {index} breaks the chain")
        if _entry_hash(entry["prev_hash"], entry["sequence"], entry["payload"]) != entry["entry_hash"]:
            raise HistoryError(f"history entry {index} hash mismatch")
        expected_prev = entry["entry_hash"]
    return len(entries)


def record(history_path: Path, rollup: dict[str, Any], *, recorded_at: str) -> dict[str, Any]:
    """Append one roll-up. `recorded_at` is supplied by the caller, never read from
    the clock, so a history can be rebuilt deterministically from its inputs."""
    required = {"program_status", "program_score", "coverage", "weight_digest"}
    missing = required - set(rollup)
    if missing:
        raise HistoryError(f"roll-up is missing {', '.join(sorted(missing))}")

    entries = read_history(history_path)
    verify_history(entries)
    sequence = len(entries)
    prev_hash = entries[-1]["entry_hash"] if entries else GENESIS_PREV

    payload = {
        "recorded_at": recorded_at,
        "program_status": rollup["program_status"],
        "program_score": rollup["program_score"],
        "coverage": rollup["coverage"],
        "weight_digest": rollup["weight_digest"],
        "readiness_state": rollup.get("readiness_state"),
        "auto_failed_teams": rollup.get("auto_failed_teams", []),
        "teams": {
            t["team"]: {"score": t["score"], "state": t["state"],
                        "evidence_completeness": t["evidence_completeness"]}
            for t in rollup.get("teams", [])
        },
    }
    entry = {
        "sequence": sequence,
        "prev_hash": prev_hash,
        "entry_hash": _entry_hash(prev_hash, sequence, payload),
        "payload": payload,
    }
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    return entry


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 4)


def trend(entries: list[dict[str, Any]]) -> dict[str, Any]:
    verify_history(entries)
    if not entries:
        return {"entries": 0, "movements": [], "notes": ["no history recorded yet"]}

    movements: list[dict[str, Any]] = []
    notes: list[str] = []
    regressions: list[str] = []

    for previous, current in zip(entries, entries[1:]):
        p, c = previous["payload"], current["payload"]
        comparable = p["weight_digest"] == c["weight_digest"]
        move: dict[str, Any] = {
            "from": p["recorded_at"],
            "to": c["recorded_at"],
            "comparable": comparable,
            "score_delta": _delta(c["program_score"], p["program_score"]) if comparable else None,
            "coverage_delta": _delta(c["coverage"], p["coverage"]) if comparable else None,
            "status": f"{p['program_status']} -> {c['program_status']}",
        }
        if not comparable:
            notes.append(
                f"{p['recorded_at']} -> {c['recorded_at']}: weight set changed; these two "
                "roll-ups are NOT comparable and no movement is claimed"
            )
        else:
            # A score that rises while coverage falls is a narrower question, not
            # an improvement. Naming it is the whole point of keeping coverage.
            if (move["score_delta"] or 0) > 0 and (move["coverage_delta"] or 0) < 0:
                notes.append(
                    f"{c['recorded_at']}: score rose {move['score_delta']:+} while coverage "
                    f"fell {move['coverage_delta']:+} - a narrower assessment, not an improvement"
                )
            per_team = []
            for team, now in c.get("teams", {}).items():
                before = p.get("teams", {}).get(team)
                if not before:
                    continue
                d = _delta(now.get("score"), before.get("score"))
                if d is not None and d < 0:
                    per_team.append(f"{team} {d:+}")
            if per_team:
                regressions.append(f"{c['recorded_at']}: " + ", ".join(per_team))
            move["team_regressions"] = per_team
        movements.append(move)

    first, last = entries[0]["payload"], entries[-1]["payload"]
    overall = (
        _delta(last["program_score"], first["program_score"])
        if first["weight_digest"] == last["weight_digest"] else None
    )
    if regressions:
        notes.append("per-team regressions: " + "; ".join(regressions))
    return {
        "entries": len(entries),
        "first_recorded": first["recorded_at"],
        "last_recorded": last["recorded_at"],
        "overall_score_delta": overall,
        "current_status": last["program_status"],
        "current_coverage": last["coverage"],
        "movements": movements,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Program capability history and drift")
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="append a roll-up to the history")
    rec.add_argument("--rollup", required=True, help="roll-up JSON (program_rollup.py --json)")
    rec.add_argument("--history", required=True)
    rec.add_argument("--at", required=True, help="ISO-8601 instant; supplied, never read from the clock")

    tr = sub.add_parser("trend", help="report drift across recorded roll-ups")
    tr.add_argument("--history", required=True)

    ver = sub.add_parser("verify", help="verify the history hash chain")
    ver.add_argument("--history", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            rollup_doc = json.loads(Path(args.rollup).read_text(encoding="utf-8"))
            entry = record(Path(args.history), rollup_doc, recorded_at=args.at)
            print(json.dumps({"recorded": entry["sequence"], "entry_hash": entry["entry_hash"]}, indent=2))
            return 0
        entries = read_history(Path(args.history))
        if args.command == "verify":
            print(f"valid history: {verify_history(entries)} entries")
            return 0
        print(json.dumps(trend(entries), indent=2, sort_keys=True))
        return 0
    except HistoryError as exc:
        print(f"HISTORY ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
