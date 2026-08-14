from __future__ import annotations

import copy
import unittest
from datetime import UTC, datetime

from blue_team.errors import ConfigurationError, ValidationError
from blue_team.source_auth import sign_event, verify_envelope


class SourceAuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "s" * 32
        self.event = {
            "event_id": "signed-1",
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "edr",
            "event_type": "heartbeat",
            "host": "host-1",
            "attributes": {},
        }
        self.policy = {
            "version": 1,
            "sources": {"edr": {"key_id": "edr-v1", "secret_env": "TEST_EDR_KEY"}},
        }

    def test_valid_envelope(self) -> None:
        envelope = sign_event(self.event, key_id="edr-v1", secret=self.secret)
        verified = verify_envelope(envelope, self.policy, environment={"TEST_EDR_KEY": self.secret})
        self.assertEqual(verified, self.event)

    def test_tampered_event_is_rejected(self) -> None:
        envelope = sign_event(self.event, key_id="edr-v1", secret=self.secret)
        tampered = copy.deepcopy(envelope)
        tampered["event"]["host"] = "other-host"
        with self.assertRaises(ValidationError):
            verify_envelope(tampered, self.policy, environment={"TEST_EDR_KEY": self.secret})

    def test_untrusted_source_is_rejected(self) -> None:
        other = {**self.event, "source": "unknown"}
        envelope = sign_event(other, key_id="edr-v1", secret=self.secret)
        with self.assertRaises(ValidationError):
            verify_envelope(envelope, self.policy, environment={"TEST_EDR_KEY": self.secret})

    def test_missing_key_fails_closed(self) -> None:
        envelope = sign_event(self.event, key_id="edr-v1", secret=self.secret)
        with self.assertRaises(ConfigurationError):
            verify_envelope(envelope, self.policy, environment={})


if __name__ == "__main__":
    unittest.main()
