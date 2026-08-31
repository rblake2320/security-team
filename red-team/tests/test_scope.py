import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from aegis_rt.models import Authorization, Engagement, Limits, Target, TargetKind
from aegis_rt.scope import ScopeError, scope_fingerprint, validate_engagement


def engagement() -> Engagement:
    return Engagement(
        "test-1",
        "owner",
        (Target(TargetKind.URL, "http://localhost:8080"),),
        ("http.security_headers",),
        Limits(),
    )


class ScopeTests(unittest.TestCase):
    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_public_target_is_denied_without_explicit_authorization(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]
        with self.assertRaisesRegex(ScopeError, "public target denied"):
            validate_engagement(engagement(), require_authorization=False)

    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_public_authorization_rejects_private_rebinding(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 80))]
        item = engagement()
        approved = replace(
            item,
            authorization=Authorization(
                "approver",
                "SEC-PUBLIC-1",
                (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                scope_fingerprint(item),
                "test-signature",
                allow_public_targets=True,
            ),
        )
        with self.assertRaisesRegex(ScopeError, "possible DNS rebinding"):
            validate_engagement(approved, require_authorization=True)

    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_public_authorization_rejects_mixed_dns_answers(self, resolve):
        resolve.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80)),
            (2, 1, 6, "", ("127.0.0.1", 80)),
        ]
        item = engagement()
        approved = replace(
            item,
            authorization=Authorization(
                "approver",
                "SEC-PUBLIC-2",
                (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                scope_fingerprint(item),
                "test-signature",
                allow_public_targets=True,
            ),
        )
        with self.assertRaisesRegex(ScopeError, "possible DNS rebinding"):
            validate_engagement(approved, require_authorization=True)

    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_authorization_is_bound_to_scope(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 8080))]
        item = engagement()
        auth = Authorization(
            "approver",
            "SEC-1",
            (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            scope_fingerprint(item),
            "test-signature",
        )
        approved = replace(item, authorization=auth)
        validate_engagement(approved, require_authorization=True)
        modified = replace(approved, limits=replace(approved.limits, max_requests=26))
        with self.assertRaisesRegex(ScopeError, "does not match"):
            validate_engagement(modified, require_authorization=True)

    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_naive_expiry_is_rejected_cleanly(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 8080))]
        item = engagement()
        approved = replace(
            item,
            authorization=Authorization("a", "t", "2099-01-01T00:00:00", scope_fingerprint(item), "test-signature"),
        )
        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_engagement(approved, require_authorization=True)

    @patch("aegis_rt.scope.socket.getaddrinfo")
    def test_url_query_is_rejected_to_prevent_secret_leakage(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 8080))]
        item = replace(
            engagement(),
            targets=(Target(TargetKind.URL, "http://localhost:8080/?token=secret"),),
        )
        with self.assertRaisesRegex(ScopeError, "query strings"):
            validate_engagement(item, require_authorization=False)

    def test_boolean_numeric_limit_is_rejected(self):
        item = replace(engagement(), limits=replace(Limits(), max_requests=True))
        with self.assertRaisesRegex(ScopeError, "must be integers"):
            validate_engagement(item, require_authorization=False)


if __name__ == "__main__":
    unittest.main()
