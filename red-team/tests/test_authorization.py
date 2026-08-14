import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from aegis_rt.authorization import (
    EVIDENCE_KEY,
    AuthorizationSignatureError,
    generate_keypair,
    sign_authorization,
    verify_authorization,
)
from aegis_rt.models import Authorization


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


if __name__ == "__main__":
    unittest.main()
