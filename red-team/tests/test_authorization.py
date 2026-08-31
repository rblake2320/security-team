import argparse
import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegis_rt.authorization import (
    EVIDENCE_KEY,
    AuthorizationSignatureError,
    generate_keypair,
    sign_authorization,
    verify_authorization,
)
from aegis_rt.cli import _authorize
from aegis_rt.models import Authorization
from aegis_rt.scope import ScopeError


class AuthorizationTests(unittest.TestCase):
    def test_signed_receipt_rejects_any_tampering_or_wrong_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "issuer.pem"
            public = root / "issuer.pub.pem"
            other_private = root / "other.pem"
            other_public = root / "other.pub.pem"
            password = b"correct horse battery staple"
            generate_keypair(private, public, password)
            generate_keypair(other_private, other_public, password)
            receipt = Authorization("owner", "SEC-7", "2099-01-01T00:00:00Z", "a" * 64, "")
            receipt = replace(receipt, signature=sign_authorization(receipt, private, password))
            verify_authorization(receipt, public)
            with self.assertRaises(AuthorizationSignatureError):
                verify_authorization(replace(receipt, ticket="SEC-8"), public)
            with self.assertRaises(AuthorizationSignatureError):
                verify_authorization(receipt, other_public)

    def test_key_generation_never_overwrites_existing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "issuer.pem"
            public = root / "issuer.pub.pem"
            generate_keypair(private, public, b"a-long-enough-password")
            original = private.read_bytes()
            with self.assertRaises(FileExistsError):
                generate_keypair(private, public, b"a-long-enough-password")
            self.assertEqual(original, private.read_bytes())

    def test_evidence_key_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "evidence.pem"
            public = root / "evidence.pub.pem"
            password = b"a-long-enough-password"
            generate_keypair(private, public, password, purpose=EVIDENCE_KEY)
            receipt = Authorization("owner", "SEC-7", "2099-01-01T00:00:00Z", "a" * 64, "")
            with self.assertRaisesRegex(AuthorizationSignatureError, "cannot be used"):
                sign_authorization(receipt, private, password)

    def test_invalid_target_is_not_persisted_as_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "issuer.pem"
            public = root / "issuer.pub.pem"
            engagement_path = root / "engagement.json"
            password_name = "AEGIS_TEST_AUTH_PASSWORD"
            password = "a-long-enough-password"
            generate_keypair(private, public, password.encode("utf-8"))
            engagement_path.write_text(
                json.dumps(
                    {
                        "engagement_id": "invalid-public-target",
                        "owner": "Security Engineering",
                        "targets": [{"kind": "url", "value": "http://127.0.0.1"}],
                        "allowed_checks": ["http.security_headers"],
                        "limits": {
                            "max_requests": 10,
                            "max_concurrency": 1,
                            "requests_per_second": 1,
                            "timeout_seconds": 5,
                            "max_files": 10,
                            "max_findings": 10,
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            original = engagement_path.read_text(encoding="utf-8")
            os.environ[password_name] = password
            try:
                args = argparse.Namespace(
                    ack="I AM AUTHORIZED",
                    engagement=engagement_path,
                    approved_by="owner",
                    ticket="SEC-TEST-1",
                    expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                    allow_public_targets=True,
                    signing_key=private,
                    password_env=password_name,
                )
                with self.assertRaisesRegex(ScopeError, "possible DNS rebinding"):
                    _authorize(args)
            finally:
                os.environ.pop(password_name, None)
            self.assertEqual(original, engagement_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
