"""Falsification tests for EXERCISE-CLEARANCE-BINDING-001.

Implements the reviewer's 15-case table. Fixture keys only; no production
authorization is forged and no production private key exists in the repo.
"""

from __future__ import annotations

import base64
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
EX = HERE.parent
sys.path.insert(0, str(EX))

import clearance as clr  # noqa: E402
import run_rehearsal  # noqa: E402

FIX = HERE / "fixtures" / "trust"
NOW = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)
RUNNER = "exercise.run_rehearsal"


def fixture_key(kid: str) -> Ed25519PrivateKey:
    raw = json.loads((FIX / "_fixture_private_keys.json").read_text(encoding="utf-8"))["keys"][kid]
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))


AUTH = {
    "schema": "purple.rehearsal-authorization/1.0",
    "exercise_id": "EX-TEST-001",
    "mode": "ENGINEERING_REHEARSAL",
    "expires_at": "2026-12-31T00:00:00+00:00",
    "allowed_test_ids": ["TC-IDOR-001"],
}
MANIFEST = [EX / "red" / "test_cases.json", EX / "blue" / "detections.json"]


class ClearanceTests(unittest.TestCase):

    def setUp(self):
        self.key = fixture_key("fixture-clearance-2026")
        self.c = clr.issue(exercise_id="EX-TEST-001", mode="ENGINEERING_REHEARSAL",
                           authorization=AUTH, manifest_paths=MANIFEST,
                           scope=AUTH["allowed_test_ids"], signing_key=self.key,
                           signing_key_id="fixture-clearance-2026",
                           runner_identity=RUNNER, now=NOW)

    def _verify(self, c=None, **over):
        kw = dict(exercise_id="EX-TEST-001", mode="ENGINEERING_REHEARSAL", authorization=AUTH,
                  manifest_paths=MANIFEST, runner_identity=RUNNER, now=NOW, consume_nonce=False)
        kw.update(over)
        return clr.verify(c or self.c, **kw)

    def _assert_refused(self, rule, fn, *a, **k):
        with self.assertRaises(clr.ClearanceError) as ctx:
            fn(*a, **k)
        self.assertIn(rule, str(ctx.exception))

    # 14. Valid fixture signatures in engineering mode -> cleared, marked nonproduction
    def test_valid_fixture_clears_engineering_mode(self):
        self._verify()
        store = clr.load_trust_store("ENGINEERING_REHEARSAL")
        self.assertEqual(store["fixture-clearance-2026"]["environment"], "TEST_ONLY")

    # 3. Correct signature from an untrusted fixture key -> REFUSED
    def test_refuses_unknown_key_even_with_valid_signature(self):
        rogue = Ed25519PrivateKey.generate()
        c = clr.issue(exercise_id="EX-TEST-001", mode="ENGINEERING_REHEARSAL", authorization=AUTH,
                      manifest_paths=MANIFEST, scope=AUTH["allowed_test_ids"], signing_key=rogue,
                      signing_key_id="not-enrolled", runner_identity=RUNNER, now=NOW)
        self._assert_refused("UNKNOWN-KEY", self._verify, c)

    def test_refuses_signer_with_wrong_role(self):
        other = fixture_key("fixture-white-2026")
        c = clr.issue(
            exercise_id="EX-TEST-001",
            mode="ENGINEERING_REHEARSAL",
            authorization=AUTH,
            manifest_paths=MANIFEST,
            scope=AUTH["allowed_test_ids"],
            signing_key=other,
            signing_key_id="fixture-white-2026",
            runner_identity=RUNNER,
            now=NOW,
        )
        self._assert_refused("KEY-ROLE", self._verify, c)

    # 2. Invalid signature -> REFUSED (InvalidSignature caught specifically)
    def test_refuses_tampered_signature(self):
        c = dict(self.c, exercise_id="EX-TEST-001", mode="ENGINEERING_REHEARSAL")
        c["approved_scope"] = ["TC-SOMETHING-ELSE"]     # body changed after signing
        self._assert_refused("CLEARANCE-SIGNATURE", self._verify, c)

    # 15. Formal mode may not load fixture keys at all
    def test_formal_mode_refuses_fixture_trust_store(self):
        self._assert_refused("TRUST-STORE", clr.load_trust_store,
                             "FORMAL_INTEGRATED_ASSESSMENT", True)

    def test_formal_mode_production_store_is_empty(self):
        store = clr.load_trust_store("FORMAL_INTEGRATED_ASSESSMENT")
        self.assertEqual(store, {}, "no production keys enrolled yet - formal mode cannot clear")

    def test_refuses_test_only_key_in_formal_mode(self):
        store = {"fixture-clearance-2026": {"key_id": "fixture-clearance-2026",
                                            "environment": "TEST_ONLY", "public_key": "AA=="}}
        self._assert_refused("TEST-KEY-IN-FORMAL", clr.resolve_key,
                             "fixture-clearance-2026", store, "FORMAL_INTEGRATED_ASSESSMENT")

    # 11. Execution mode changed after clearance -> runner refuses.
    # Refused at the TRUST STORE first: a fixture-signed clearance cannot be resolved
    # in formal mode at all. That is a stronger refusal than the mode-binding check,
    # which still guards mode changes within one trust store.
    def test_refuses_mode_change_after_clearance(self):
        self._assert_refused("UNKNOWN-KEY", self._verify, None,
                             mode="FORMAL_INTEGRATED_ASSESSMENT")

    def test_mode_binding_refuses_within_one_trust_store(self):
        c = dict(self.c, mode="SOMETHING_ELSE")
        self._assert_refused("CLEARANCE-SIGNATURE", self._verify, c)

    # 7. Target/exercise differs -> REFUSED
    def test_refuses_exercise_id_change(self):
        self._assert_refused("CLEARANCE-EXERCISE", self._verify, None, exercise_id="EX-OTHER")

    # 8. Technique absent from signed scope -> authorization digest changes -> REFUSED
    def test_refuses_scope_change(self):
        self._assert_refused("CLEARANCE-AUTHORIZATION", self._verify, None,
                             authorization=dict(AUTH, allowed_test_ids=["TC-EXTRA-002"]))

    # 4/5. Authorization expiry rebinding
    def test_refuses_authorization_expiry_change(self):
        self._assert_refused("CLEARANCE-AUTHORIZATION", self._verify, None,
                             authorization=dict(AUTH, expires_at="2030-01-01T00:00:00+00:00"))

    # 10. Manifest/input digest changed after clearance -> runner refuses
    def test_refuses_manifest_change_after_clearance(self):
        self._assert_refused("CLEARANCE-MANIFEST", self._verify, None,
                             manifest_paths=[EX / "purple" / "traceability.json"])

    # 10b. Safety-boundary config digest changed after clearance
    def test_refuses_boundary_config_change(self):
        tmp = EX / "config" / "_tmp_boundaries.json"
        tmp.write_text('{"boundaries": []}', encoding="utf-8")
        try:
            self._assert_refused("CLEARANCE-BOUNDARIES", self._verify, None, boundaries_path=tmp)
        finally:
            tmp.unlink()

    # 6. Revocation-list digest changed after clearance
    def test_refuses_revocation_list_change(self):
        tmp = EX / "config" / "_tmp_revs.json"
        tmp.write_text('{"revocations": [{"revocation_id": "REV-X"}]}', encoding="utf-8")
        try:
            self._assert_refused("CLEARANCE-REVOCATIONS", self._verify, None, revocations_path=tmp)
        finally:
            tmp.unlink()

    def test_refuses_runner_identity_change(self):
        self._assert_refused("CLEARANCE-RUNNER", self._verify, None, runner_identity="some.other.runner")

    # Short-lived: expired clearance
    def test_refuses_expired_clearance(self):
        self._assert_refused("CLEARANCE-EXPIRED", self._verify, None,
                             now=NOW + timedelta(seconds=clr.CLEARANCE_TTL_SECONDS + 1))

    def test_refuses_clearance_used_before_issue(self):
        self._assert_refused("CLEARANCE-EXPIRED", self._verify, None, now=NOW - timedelta(minutes=5))

    # 12. Reuse of clearance nonce -> runner refuses
    def test_refuses_nonce_replay(self):
        ledger = clr.NONCE_LEDGER
        backup = ledger.read_text(encoding="utf-8") if ledger.exists() else None
        try:
            self._verify(consume_nonce=True)                       # first use ok
            self._assert_refused("CLEARANCE-REPLAY", self._verify, None, consume_nonce=True)
        finally:
            if backup is None:
                ledger.unlink(missing_ok=True)
            else:
                ledger.write_text(backup, encoding="utf-8")

    # 13. Direct invocation of run_rehearsal.py -> runner refuses
    def test_direct_runner_invocation_is_refused(self):
        missing = EX / "evidence" / "_no_such_clearance.json"
        self.assertFalse(missing.exists())
        with self.assertRaises(clr.ClearanceError) as ctx:
            run_rehearsal.run(write_evidence=False, clearance_path=missing)
        self.assertIn("NO-CLEARANCE", str(ctx.exception))

    # 1/9. Production gate attestations absent -> formal mode cannot clear
    def test_formal_mode_cannot_clear_without_production_authorities(self):
        self.assertEqual(clr.load_trust_store("FORMAL_INTEGRATED_ASSESSMENT"), {})
        self._assert_refused("UNKNOWN-KEY", self._verify, None,
                             mode="FORMAL_INTEGRATED_ASSESSMENT",
                             exercise_id="EX-TEST-001")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class NonceLedgerTests(unittest.TestCase):
    """Falsification tests for the production nonce-ledger behaviour."""

    def setUp(self):
        self.ledger = clr.NONCE_LEDGER
        self.backup = self.ledger.read_text(encoding="utf-8") if self.ledger.exists() else None

    def tearDown(self):
        if self.backup is None:
            self.ledger.unlink(missing_ok=True)
        else:
            self.ledger.write_text(self.backup, encoding="utf-8")

    def test_expired_nonces_are_pruned(self):
        """Entries older than the retention window are dropped; a clearance that old
        is already refused by the expiry check, so retaining it adds nothing."""
        old = (NOW - timedelta(seconds=clr.NONCE_RETENTION_SECONDS + 60)).isoformat()
        fresh = NOW.isoformat()
        pruned = clr._prune({"old": {"at": old}, "fresh": {"at": fresh}}, NOW)
        self.assertNotIn("old", pruned)
        self.assertIn("fresh", pruned)

    def test_unparsable_entries_are_retained_never_discarded(self):
        """NEGATIVE. An entry we cannot age out must never be silently dropped."""
        pruned = clr._prune({"weird": {"at": "not-a-timestamp"}, "missing": {}}, NOW)
        self.assertEqual(set(pruned), {"weird", "missing"})

    def test_corrupt_ledger_fails_closed(self):
        """NEGATIVE. Starting fresh on a corrupt ledger would reopen every past nonce."""
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("{not json", encoding="utf-8")
        with self.assertRaises(clr.ClearanceError) as ctx:
            clr.consume("any-nonce", "EX-TEST-001", now=NOW)
        self.assertIn("LEDGER-CORRUPT", str(ctx.exception))

    def test_replay_still_refused_within_retention(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("{}", encoding="utf-8")
        clr.consume("n1", "EX-TEST-001", now=NOW)
        with self.assertRaises(clr.ClearanceError) as ctx:
            clr.consume("n1", "EX-TEST-001", now=NOW)
        self.assertIn("CLEARANCE-REPLAY", str(ctx.exception))
