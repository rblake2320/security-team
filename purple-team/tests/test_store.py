from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aegis_purple.errors import IntegrityError, TransitionError
from aegis_purple.models import ExercisePlan, ExerciseState
from aegis_purple.store import ExerciseStore
from test_models import plan_data


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "purple.db"
        self.store = ExerciseStore(self.db)
        self.plan = ExercisePlan.from_dict(plan_data())
        self.store.create_exercise(self.plan, actor_id="purple-lead")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def transition(self, source: ExerciseState, target: ExerciseState, role: str) -> None:
        self.store.transition(
            self.plan.exercise_id, target, actor_id=f"{role}-one", actor_role=role,
            reason="authorized test transition", expected_state=source,
        )

    def test_state_skipping_is_rejected(self) -> None:
        with self.assertRaises(TransitionError):
            self.transition(ExerciseState.FROZEN, ExerciseState.EXECUTING, "purple")

    def test_purple_cannot_self_authorize(self) -> None:
        with self.assertRaises(TransitionError):
            self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "purple")

    def test_plan_owner_cannot_act_as_white_authority(self) -> None:
        with self.assertRaises(TransitionError):
            self.store.transition(
                self.plan.exercise_id, ExerciseState.AUTHORIZED, actor_id=self.plan.owner,
                actor_role="white", reason="conflicted approval", expected_state=ExerciseState.FROZEN,
            )

    def test_stale_transition_is_rejected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        with self.assertRaises(TransitionError):
            self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")

    def test_white_can_stop_without_execution(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.STOPPED, "white")
        self.assertEqual(self.store.status(self.plan.exercise_id)["state"], "STOPPED")

    def test_conflicting_plan_replay_is_rejected(self) -> None:
        data = plan_data()
        data["title"] = "Changed after freeze"
        with self.assertRaises(TransitionError):
            self.store.create_exercise(ExercisePlan.from_dict(data), actor_id="purple-lead")

    def test_evidence_outside_frozen_test_case_is_rejected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        with self.assertRaises(IntegrityError):
            self.store.add_evidence(
                self.plan.exercise_id, evidence_id="EV-001", test_case_id="TC-OUTSIDE",
                artifact_sha256="e" * 64, producer_id="sensor", producer_role="system",
                media_type="application/json",
            )

    def test_cross_test_case_evidence_is_rejected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        self.store.add_evidence(
            self.plan.exercise_id, evidence_id="EV-001", test_case_id="TC-2026-001",
            artifact_sha256="e" * 64, producer_id="sensor", producer_role="system",
            media_type="application/json",
        )
        with self.assertRaises(IntegrityError):
            self.store.record_result(
                self.plan.exercise_id, test_case_id="TC-DIFFERENT", stage="logged",
                outcome="pass", evidence_id="EV-001",
            )

    def test_evidence_verification_requires_all_six_stages(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        self.transition(ExerciseState.EXECUTING, ExerciseState.EXECUTED, "purple")
        with self.assertRaises(TransitionError):
            self.transition(ExerciseState.EXECUTED, ExerciseState.EVIDENCE_VERIFIED, "exercise_assurance")

    def test_tail_deletion_is_detected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.store.connection.execute("DELETE FROM transitions WHERE sequence = 2")
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_interior_transition_deletion_is_detected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        self.store.connection.execute("DELETE FROM transitions WHERE sequence = 2")
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_transition_mutation_is_detected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.store.connection.execute("UPDATE transitions SET reason = 'rewritten' WHERE sequence = 2")
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_plan_tampering_is_detected(self) -> None:
        self.store.connection.execute(
            "UPDATE exercises SET plan_json = replace(plan_json, 'Identity', 'Altered') WHERE exercise_id = ?",
            (self.plan.exercise_id,),
        )
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_direct_state_tampering_is_detected(self) -> None:
        self.store.connection.execute(
            "UPDATE exercises SET state = 'CLOSED' WHERE exercise_id = ?", (self.plan.exercise_id,)
        )
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_evidence_tampering_is_detected(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        self.store.add_evidence(
            self.plan.exercise_id, evidence_id="EV-001", test_case_id="TC-2026-001",
            artifact_sha256="e" * 64, producer_id="sensor", producer_role="system",
            media_type="application/json",
        )
        self.store.connection.execute(
            "UPDATE evidence SET artifact_sha256 = ? WHERE evidence_id = 'EV-001'", ("a" * 64,)
        )
        self.store.connection.commit()
        with self.assertRaises(IntegrityError):
            self.store.verify()

    def test_complete_lifecycle_requires_independent_evidence_verifier(self) -> None:
        self.transition(ExerciseState.FROZEN, ExerciseState.AUTHORIZED, "white")
        self.transition(ExerciseState.AUTHORIZED, ExerciseState.EXECUTING, "purple")
        self.store.add_evidence(
            self.plan.exercise_id, evidence_id="EV-001", test_case_id="TC-2026-001",
            artifact_sha256="e" * 64, producer_id="sensor", producer_role="system",
            media_type="application/json",
        )
        for stage in ("prevented", "logged", "alerted", "investigated", "contained", "reported"):
            self.store.record_result(
                self.plan.exercise_id, test_case_id="TC-2026-001", stage=stage,
                outcome="pass", evidence_id="EV-001",
            )
        self.transition(ExerciseState.EXECUTING, ExerciseState.EXECUTED, "purple")
        with self.assertRaises(TransitionError):
            self.store.transition(
                self.plan.exercise_id, ExerciseState.EVIDENCE_VERIFIED,
                actor_id="purple-one", actor_role="exercise_assurance", reason="conflicted",
                expected_state=ExerciseState.EXECUTED,
            )
        self.transition(ExerciseState.EXECUTED, ExerciseState.EVIDENCE_VERIFIED, "exercise_assurance")
        self.transition(ExerciseState.EVIDENCE_VERIFIED, ExerciseState.RETESTED, "purple")
        self.transition(ExerciseState.RETESTED, ExerciseState.CLOSED, "white")
        self.assertTrue(self.store.verify()["valid"])


if __name__ == "__main__":
    unittest.main()
