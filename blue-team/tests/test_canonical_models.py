from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta

from blue_team.canonical import MAX_EVENT_BYTES, loads_bounded, normalize
from blue_team.errors import ValidationError
from blue_team.models import Event


class CanonicalizationTests(unittest.TestCase):
    def test_rejects_oversized_event(self) -> None:
        with self.assertRaises(ValidationError):
            loads_bounded(b'"' + b"a" * MAX_EVENT_BYTES + b'"')

    def test_rejects_unicode_key_collision(self) -> None:
        with self.assertRaises(ValidationError):
            normalize({"K": 1, "K": 2})

    def test_rejects_excessive_nesting(self) -> None:
        value: object = "leaf"
        for _ in range(10):
            value = {"next": value}
        with self.assertRaises(ValidationError):
            normalize(value)

    def test_rejects_non_finite_number(self) -> None:
        with self.assertRaises(ValidationError):
            normalize({"score": float("nan")})


class EventModelTests(unittest.TestCase):
    def base(self) -> dict[str, object]:
        return {
            "event_id": "evt-1",
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "edr",
            "event_type": "process_start",
            "host": "host-1",
            "attributes": {},
        }

    def test_rejects_unknown_top_level_field(self) -> None:
        data = self.base()
        data["unexpected"] = "value"
        with self.assertRaises(ValidationError):
            Event.from_dict(data)

    def test_rejects_timezone_free_timestamp(self) -> None:
        data = self.base()
        data["timestamp"] = "2026-08-13T12:00:00"
        with self.assertRaises(ValidationError):
            Event.from_dict(data)

    def test_rejects_implausible_future_timestamp(self) -> None:
        data = self.base()
        data["timestamp"] = (datetime.now(UTC) + timedelta(days=8)).isoformat()
        with self.assertRaises(ValidationError):
            Event.from_dict(data)

    def test_valid_event_round_trip(self) -> None:
        event = Event.from_dict(json.loads(json.dumps(self.base())))
        self.assertEqual(event.host, "host-1")
        self.assertEqual(event.severity, 0)


if __name__ == "__main__":
    unittest.main()
