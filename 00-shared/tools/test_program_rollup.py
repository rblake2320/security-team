"""Program roll-up: the five published scorecard rules, tested as rules.

Each test names the rule it defends. If a rule is ever quietly relaxed, the test
that fails should say which governance statement was broken.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from program_rollup import (  # noqa: E402
    CHALLENGE_REVIEW_THRESHOLD,
    EVIDENCE_COMPLETENESS_FLOOR,
    RollupError,
    TEAMS,
    load_scorecards,
    rollup,
    verify_weights,
    weight_digest,
)


def score_doc(team: str, value: float, *, auto_failures=None, demonstrated=4, total=5):
    components = [
        {"key": f"C{i}", "name": "c", "weight": 0.2,
         "value": value, "status": "scored" if i < demonstrated else "not_demonstrated",
         "detail": ""}
        for i in range(total)
    ]
    return {
        "team": team, "status": "PASS", "weighted_score": value,
        "auto_failures": list(auto_failures or []), "components": components,
    }


def write_scores(directory: Path, docs: list[dict]) -> Path:
    for doc in docs:
        (directory / f"{doc['team']}.json").write_text(json.dumps(doc), encoding="utf-8")
    return directory


class TestPublishedWeights(unittest.TestCase):
    def test_the_seven_published_weights_sum_to_one(self):
        # The whole roll-up is meaningless if they do not.
        self.assertAlmostEqual(verify_weights(load_scorecards()), 1.0, places=9)

    def test_every_team_publishes_a_program_weight(self):
        cards = load_scorecards()
        for team in TEAMS:
            self.assertIn("program_weight_7team", cards[team], f"{team} publishes no weight")

    def test_weight_digest_changes_when_a_weight_changes(self):
        """Rule 1: weights are FROZEN at execution start. The digest is what makes a
        later change detectable instead of silently reshaping past results."""
        cards = load_scorecards()
        before = weight_digest(cards)
        cards["red"] = dict(cards["red"], program_weight_7team=0.2)
        self.assertNotEqual(before, weight_digest(cards))

    def test_inconsistent_weights_are_refused(self):
        cards = load_scorecards()
        cards["red"] = dict(cards["red"], program_weight_7team=0.5)
        with self.assertRaises(RollupError):
            verify_weights(cards)


class TestRuleTwoAutoFailBeatsAggregation(unittest.TestCase):
    def test_one_team_auto_fail_fails_the_whole_program(self):
        cards = load_scorecards()
        docs = [score_doc(t, 1.0) for t in TEAMS]
        docs[TEAMS.index("green")]["auto_failures"] = ["critical telemetry below 100%"]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertEqual(result["program_status"], "FAILED")
        self.assertEqual(result["auto_failed_teams"], ["green"])

    def test_the_weighted_score_is_retained_for_diagnostics(self):
        """The rule says the score is retained for diagnostics only - not discarded,
        and not allowed to override the failure."""
        cards = load_scorecards()
        docs = [score_doc(t, 1.0) for t in TEAMS]
        docs[TEAMS.index("red")]["auto_failures"] = ["ran without a valid receipt"]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertEqual(result["program_status"], "FAILED")
        self.assertGreater(result["program_score"], 0.9)


class TestRuleThreeEvidenceCompleteness(unittest.TestCase):
    def test_the_floor_is_the_value_these_tests_assume(self):
        # The fixtures below use 1-of-5 and 4-of-5 demonstrated components, which only
        # straddle the boundary while the floor sits at one half. Pin it so a future
        # change to the constant fails here rather than silently reinterpreting them.
        self.assertEqual(EVIDENCE_COMPLETENESS_FLOOR, 0.5)

    def test_mostly_undemonstrated_team_yields_insufficient_evidence(self):
        cards = load_scorecards()
        docs = [score_doc(t, 1.0) for t in TEAMS]
        docs[TEAMS.index("orange")] = score_doc("orange", 1.0, demonstrated=1, total=5)
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertEqual(result["program_status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("orange", result["insufficient_evidence_teams"])

    def test_an_undemonstrated_team_does_not_inflate_the_program_score(self):
        """A perfect score derived from one demonstrated component out of five must
        not be aggregated as if it were evidence."""
        cards = load_scorecards()
        strong = [score_doc(t, 0.5) for t in TEAMS if t != "white"]
        hollow = score_doc("white", 1.0, demonstrated=1, total=5)
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), strong + [hollow]))
        result = rollup(cards, scores)
        self.assertAlmostEqual(result["program_score"], 0.5, places=6)


class TestRuleFourChallengeReview(unittest.TestCase):
    def test_a_very_high_score_is_not_a_pass(self):
        cards = load_scorecards()
        docs = [score_doc(t, 0.99) for t in TEAMS]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertEqual(result["program_status"], "CHALLENGE_REVIEW_REQUIRED")
        self.assertTrue(any("challenge review" in n for n in result["notes"]))

    def test_just_below_the_threshold_is_merely_scored(self):
        cards = load_scorecards()
        docs = [score_doc(t, CHALLENGE_REVIEW_THRESHOLD - 0.01) for t in TEAMS]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        self.assertEqual(rollup(cards, scores)["program_status"], "SCORED")


class TestPartialAssessment(unittest.TestCase):
    def test_absent_teams_are_renormalized_not_assumed(self):
        cards = load_scorecards()
        docs = [score_doc(t, 0.8) for t in ("red", "blue", "purple")]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertAlmostEqual(result["program_score"], 0.8, places=6)
        # Coverage must expose that most of the program was never looked at.
        self.assertLess(result["coverage"], 0.5)
        self.assertTrue(any("not assessed" in n for n in result["notes"]))

    def test_unknown_team_document_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.json").write_text(json.dumps({"team": "chartreuse"}), encoding="utf-8")
            from program_rollup import load_scores
            with self.assertRaises(RollupError):
                load_scores(Path(tmp))


class TestAssuranceIsGatedByReadiness(unittest.TestCase):
    def test_assurance_is_prohibited_while_readiness_gates_are_unmet(self):
        """The program is PREREQUISITES_PENDING. A diagnostic number must never be
        presentable as assurance while that holds."""
        cards = load_scorecards()
        docs = [score_doc(t, 1.0) for t in TEAMS]
        with tempfile.TemporaryDirectory() as tmp:
            from program_rollup import load_scores
            scores = load_scores(write_scores(Path(tmp), docs))
        result = rollup(cards, scores)
        self.assertFalse(result["assurance_permitted"])
        self.assertEqual(result["marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")


if __name__ == "__main__":
    unittest.main()
