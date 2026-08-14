from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from blue_team.coverage import coverage_report, load_coverage_target
from blue_team.detection import DetectionEngine, load_rules
from blue_team.errors import ConfigurationError
from blue_team.health import health_report
from blue_team.models import Event
from blue_team.response import load_playbooks, response_plan
from blue_team.store import EvidenceStore

ROOT = Path(__file__).resolve().parents[1]


class OperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = EvidenceStore(Path(self.temp.name) / "blue.db")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_health_reports_missing_and_stale_sensors(self) -> None:
        old = datetime.now(UTC) - timedelta(hours=1)
        item = Event.from_dict(
            {
                "event_id": "health-1",
                "timestamp": old.isoformat(),
                "source": "edr",
                "event_type": "heartbeat",
                "host": "host-1",
                "attributes": {},
            }
        )
        self.store.add_event(item)
        report = health_report(
            self.store,
            [
                {"source": "edr", "host": "*", "max_age_seconds": 60},
                {"source": "dns", "host": "*", "max_age_seconds": 60},
            ],
        )
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["blind_spots"][0]["status"], "missing")
        self.assertTrue(any(row["source"] == "edr" and row["status"] == "healthy" for row in report["sensors"]))

    def test_future_event_time_cannot_extend_sensor_freshness(self) -> None:
        item = Event.from_dict(
            {
                "event_id": "future-health",
                "timestamp": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "source": "edr",
                "event_type": "heartbeat",
                "host": "host-1",
                "attributes": {},
            }
        )
        self.store.add_event(item)
        report = health_report(
            self.store,
            [{"source": "edr", "host": "*", "max_age_seconds": 60}],
            now=datetime.now(UTC) + timedelta(minutes=2),
        )
        self.assertEqual(report["sensors"][0]["status"], "stale")

    def test_coverage_target_and_all_tactics_are_mapped(self) -> None:
        rules = load_rules(ROOT / "rules")
        target = load_coverage_target(ROOT / "config" / "coverage_target.json")
        report = coverage_report(rules, target)
        self.assertEqual(report["total"], len(target))
        self.assertEqual(report["gaps"], [])
        self.assertEqual(report["tactic_gaps"], [])

    def test_response_is_non_executing_and_two_person_for_high_risk(self) -> None:
        plans = load_playbooks(ROOT / "playbooks" / "playbooks.json")
        plan = response_plan(plans, "ransomware", {"alert_id": "alert-1", "severity": "critical"})
        self.assertFalse(plan["execution_enabled"])
        isolate = next(step for step in plan["steps"] if step["action"] == "isolate_host")
        self.assertTrue(isolate["approval_required"])
        self.assertEqual(isolate["minimum_approvers"], 2)
        self.assertTrue(isolate["rollback"])

    def test_unknown_response_action_fails_closed(self) -> None:
        with self.assertRaises(ConfigurationError):
            response_plan(
                {"bad": {"steps": [{"action": "isolate-host", "description": "typo"}]}},
                "bad",
                {"alert_id": "alert-1", "severity": "critical"},
            )

    def test_large_untrusted_transfer_alerts(self) -> None:
        engine = DetectionEngine(self.store, load_rules(ROOT / "rules"))
        item = Event.from_dict(
            {
                "event_id": "transfer-1",
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "firewall",
                "event_type": "network_transfer",
                "host": "host-1",
                "attributes": {
                    "direction": "outbound",
                    "destination_trusted": False,
                    "destination": "198.51.100.8",
                    "bytes": 200_000_000,
                },
            }
        )
        self.store.add_event(item)
        alerts = engine.evaluate(item)
        self.assertEqual([alert.rule_id for alert in alerts], ["BT-NETWORK-002"])


if __name__ == "__main__":
    unittest.main()
