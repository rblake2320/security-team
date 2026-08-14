from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from blue_team.detection import DetectionEngine, load_rules, parse_rule, verify_rule_manifest
from blue_team.errors import ConfigurationError, IntegrityError, ValidationError
from blue_team.models import Event
from blue_team.store import EvidenceStore

ROOT = Path(__file__).resolve().parents[1]


def event(
    event_id: str,
    event_type: str,
    *,
    offset: int = 0,
    source: str = "identity",
    host: str = "host-1",
    user: str | None = "alex",
    attributes: dict[str, object] | None = None,
) -> Event:
    return Event.from_dict(
        {
            "event_id": event_id,
            "timestamp": (datetime.now(UTC) + timedelta(seconds=offset)).isoformat(),
            "source": source,
            "event_type": event_type,
            "host": host,
            "user": user,
            "attributes": attributes or {},
        }
    )


class DetectionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "blue.db"
        self.store = EvidenceStore(self.db)
        self.rules = load_rules(ROOT / "rules")
        self.engine = DetectionEngine(self.store, self.rules)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def add(self, item: Event) -> list:
        self.assertTrue(self.store.add_event(item))
        return self.engine.evaluate(item)

    def test_threshold_correlates_split_failures(self) -> None:
        alerts = []
        for index in range(8):
            alerts.extend(self.add(event(f"auth-{index}", "AUTHENTICATION_FAILED", offset=index * 5)))
        matching = [alert for alert in alerts if alert.rule_id == "BT-IDENTITY-001"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(len(matching[0].event_ids), 8)

    def test_threshold_does_not_mix_users(self) -> None:
        alerts = []
        for index in range(10):
            user = "alex" if index % 2 else "sam"
            alerts.extend(self.add(event(f"mixed-{index}", "authentication_failed", offset=index, user=user)))
        self.assertFalse(any(alert.rule_id == "BT-IDENTITY-001" for alert in alerts))

    def test_exact_duplicate_is_idempotent(self) -> None:
        item = event("same", "identity_risk", attributes={"risk": "high"})
        self.assertTrue(self.store.add_event(item))
        self.assertEqual(len(self.engine.evaluate(item)), 1)
        self.assertFalse(self.store.add_event(item))
        self.assertEqual(len(self.store.list_alerts()), 1)

    def test_conflicting_replay_is_rejected(self) -> None:
        first = event("collision", "authentication_failed")
        second = event("collision", "identity_risk", attributes={"risk": "high"})
        self.assertTrue(self.store.add_event(first))
        with self.assertRaises(IntegrityError):
            self.store.add_event(second)

    def test_critical_rule_is_not_suppressed(self) -> None:
        alerts = []
        for index in range(2):
            item = event(
                f"impair-{index}",
                "security_control_changed",
                offset=index,
                source="edr",
                attributes={"state": "disabled"},
            )
            alerts.extend(self.add(item))
        matching = [alert for alert in alerts if alert.rule_id == "BT-ENDPOINT-001"]
        self.assertEqual(len(matching), 2)

    def test_unsafe_operator_is_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            parse_rule(
                {
                    "id": "bad-rule",
                    "title": "Bad rule",
                    "severity": "high",
                    "conditions": [{"field": "host", "operator": "regex", "value": ".*"}],
                    "techniques": [],
                    "tactics": [],
                    "rationale": "invalid",
                }
            )

    def test_string_false_cannot_enable_or_disable_policy(self) -> None:
        with self.assertRaises(ConfigurationError):
            parse_rule(
                {
                    "id": "typed-boolean",
                    "title": "Typed boolean",
                    "severity": "high",
                    "enabled": "false",
                    "conditions": [{"field": "host", "operator": "eq", "value": "x"}],
                    "techniques": ["T1003"],
                    "tactics": ["Credential Access"],
                    "rationale": "invalid boolean confusion",
                }
            )

    def test_critical_suppression_configuration_is_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            parse_rule(
                {
                    "id": "bad-critical",
                    "title": "Bad critical",
                    "severity": "critical",
                    "conditions": [{"field": "host", "operator": "eq", "value": "x"}],
                    "techniques": [],
                    "tactics": [],
                    "rationale": "invalid",
                }
            )

    def test_audit_chain_detects_mutation(self) -> None:
        self.add(event("audit-1", "identity_risk", attributes={"risk": "high"}))
        self.assertTrue(self.store.verify_audit_chain()["valid"])
        self.store.connection.execute("UPDATE audit_chain SET subject = 'tampered' WHERE sequence = 1")
        with self.assertRaises(IntegrityError):
            self.store.verify_audit_chain()

    def test_audit_chain_detects_interior_deletion(self) -> None:
        self.add(event("audit-a", "authentication_failed"))
        self.add(event("audit-b", "authentication_failed", offset=1))
        self.store.connection.execute("PRAGMA foreign_keys = OFF")
        self.store.connection.execute("DELETE FROM audit_chain WHERE sequence = 1")
        with self.assertRaises(IntegrityError):
            self.store.verify_audit_chain()

    def test_audit_chain_detects_tail_deletion(self) -> None:
        self.add(event("tail-a", "authentication_failed"))
        self.add(event("tail-b", "authentication_failed", offset=1))
        self.store.connection.execute("DELETE FROM audit_chain WHERE sequence = 2")
        with self.assertRaises(IntegrityError):
            self.store.verify_audit_chain()

    def test_correlation_survives_engine_restart_and_unrelated_flood(self) -> None:
        alerts = []
        for index in range(7):
            alerts.extend(self.add(event(f"restart-{index}", "authentication_failed", offset=index, user="target")))
        for index in range(200):
            self.add(event(f"noise-{index}", "authentication_failed", offset=index, user=f"noise-{index}"))
        restarted = DetectionEngine(self.store, load_rules(ROOT / "rules"))
        final = event("restart-final", "authentication_failed", offset=201, user="target")
        self.store.add_event(final)
        alerts.extend(restarted.evaluate(final))
        self.assertTrue(any(alert.rule_id == "BT-IDENTITY-001" for alert in alerts))

    def test_database_rejects_invalid_case_status(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "INSERT INTO cases VALUES ('x','x','low','fake','2026-01-01','2026-01-01')"
            )

    def test_case_links_to_alert(self) -> None:
        alert = self.add(event("case-event", "identity_risk", attributes={"risk": "high"}))[0]
        case = self.store.create_case(alert.alert_id, "Investigate identity risk")
        self.assertEqual(case["alert_id"], alert.alert_id)
        self.assertEqual(self.store.list_cases()[0]["alert_ids"], [alert.alert_id])

    def test_case_title_is_bounded(self) -> None:
        alert = self.add(event("case-title-event", "identity_risk", attributes={"risk": "high"}))[0]
        with self.assertRaises(ValidationError):
            self.store.create_case(alert.alert_id, "x" * 201)

    def test_rules_are_unique_and_load(self) -> None:
        ids = [rule.rule_id for rule in self.rules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 15)

    def test_rule_manifest_rejects_tampering(self) -> None:
        result = verify_rule_manifest(ROOT / "rules", ROOT / "config" / "rule_manifest.json")
        self.assertTrue(result["valid"])
        copied_rules = Path(self.temp.name) / "rules"
        copied_rules.mkdir()
        for source in (ROOT / "rules").glob("*.json"):
            (copied_rules / source.name).write_bytes(source.read_bytes())
        target = copied_rules / "endpoint.json"
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(ConfigurationError):
            verify_rule_manifest(copied_rules, ROOT / "config" / "rule_manifest.json")


if __name__ == "__main__":
    unittest.main()
