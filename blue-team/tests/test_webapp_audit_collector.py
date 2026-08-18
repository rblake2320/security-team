"""The web-application audit-log collector.

The property under test is conservatism: the collector must not upgrade an
ordinary request into a specific security event. Detection content built on a
generous mapping produces confident alerts about events that never happened.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

from webapp_audit_log import classify, collect, to_event  # noqa: E402


def row(**overrides):
    base = {
        "id": 1, "occurred_at": "2026-08-18 01:00:00", "method": "POST",
        "path": "/api/problems", "action": "problem.create", "username": None,
        "outcome": "accepted", "http_status": 200, "reason": None,
        "target_type": "problem", "target_id": 5, "quarantined": 0, "ip_hash": "abc",
    }
    base.update(overrides)
    return base


class TestClassification(unittest.TestCase):
    def test_failed_login_is_an_authentication_failure(self):
        self.assertEqual(classify(row(path="/api/auth/login", http_status=401)),
                         "authentication_failed")

    def test_successful_login_is_not_a_failure(self):
        self.assertEqual(classify(row(path="/api/auth/login", http_status=200)),
                         "authentication_succeeded")

    def test_refused_admin_request_is_an_unauthorized_privileged_attempt(self):
        self.assertEqual(classify(row(path="/api/admin/activity-log", http_status=403)),
                         "unauthorized_privileged_attempt")

    def test_successful_admin_request_is_not_upgraded(self):
        """A legitimate admin call is not an 'unauthorized attempt'. Classifying it
        as one would make every normal operator action look like an incident."""
        self.assertEqual(classify(row(path="/api/admin/activity-log", http_status=200)),
                         "api_request")

    def test_ordinary_request_stays_ordinary(self):
        self.assertEqual(classify(row()), "api_request")

    def test_deletion_is_recognised(self):
        self.assertEqual(classify(row(action="problem.delete", method="DELETE")),
                         "content_deleted")


class TestEventShape(unittest.TestCase):
    def test_required_blue_fields_are_present(self):
        event = to_event(row(), host="h", source="s")
        for field in ("event_id", "timestamp", "source", "event_type", "host"):
            self.assertIn(field, event)

    def test_timestamp_gains_a_zone_designator(self):
        self.assertEqual(to_event(row(), host="h", source="s")["timestamp"],
                         "2026-08-18T01:00:00Z")

    def test_quarantined_rows_arrive_pre_elevated(self):
        self.assertGreater(
            to_event(row(quarantined=1), host="h", source="s")["severity"],
            to_event(row(quarantined=0), host="h", source="s")["severity"],
        )

    def test_attempted_identifier_is_carried_for_failed_auth(self):
        """Without this a brute-force alert cannot say which account was targeted."""
        event = to_event(
            row(path="/api/auth/login", http_status=401, username="victim"),
            host="h", source="s",
        )
        self.assertEqual(event["user"], "victim")
        self.assertEqual(event["event_type"], "authentication_failed")

    def test_only_the_ip_hash_is_emitted(self):
        event = to_event(row(), host="h", source="s")
        self.assertEqual(event["attributes"]["ip_hash"], "abc")
        self.assertNotIn("ip", event["attributes"])

    def test_event_ids_are_unique_per_row(self):
        events = collect([row(id=1), row(id=2)], host="h", source="s")
        self.assertEqual(len({e["event_id"] for e in events}), 2)


if __name__ == "__main__":
    unittest.main()
