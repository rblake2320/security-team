import json
import tempfile
import unittest
from pathlib import Path

from aegis_rt.audit import AuditLedger, seal_ledger, verify_ledger_seal
from aegis_rt.authorization import AUTHORIZATION_KEY, EVIDENCE_KEY, AuthorizationSignatureError, generate_keypair


class AuditLedgerTests(unittest.TestCase):
    def test_chain_verifies_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            ledger = AuditLedger(path)
            ledger.append("one", {"value": 1})
            ledger.append("two", {"value": 2})
            self.assertEqual((True, 2, None), ledger.verify())

            records = path.read_text(encoding="utf-8").splitlines()
            first = json.loads(records[0])
            first["data"]["value"] = 99
            records[0] = json.dumps(first)
            path.write_text("\n".join(records) + "\n", encoding="utf-8")
            valid, count, error = ledger.verify()
            self.assertFalse(valid)
            self.assertEqual(0, count)
            self.assertIn("hash mismatch", error)
            with self.assertRaisesRegex(ValueError, "refusing to append"):
                ledger.append("three", {})

    def test_chain_detects_interior_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            ledger = AuditLedger(path)
            ledger.append("one", {"value": 1})
            ledger.append("two", {"value": 2})
            ledger.append("three", {"value": 3})
            records = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join((records[0], records[2])) + "\n", encoding="utf-8")
            valid, count, error = ledger.verify()
            self.assertFalse(valid)
            self.assertEqual(1, count)
            self.assertIn("broken chain", error)

    def test_signed_seal_rejects_recomputed_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path = root / "audit.jsonl"
            seal_path = root / "audit.seal.json"
            private = root / "issuer.pem"
            public = root / "issuer.pub.pem"
            password = b"a-long-ledger-password"
            generate_keypair(private, public, password, purpose=EVIDENCE_KEY)
            ledger = AuditLedger(ledger_path)
            ledger.append("one", {"value": 1})
            seal_ledger(ledger_path, seal_path, private, password)
            verify_ledger_seal(ledger_path, seal_path, public)
            ledger_path.write_text(ledger_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                verify_ledger_seal(ledger_path, seal_path, public)
            with self.assertRaises(FileExistsError):
                seal_ledger(ledger_path, seal_path, private, password)

    def test_authorization_key_cannot_seal_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path = root / "audit.jsonl"
            private = root / "authorization.pem"
            public = root / "authorization.pub.pem"
            password = b"a-long-ledger-password"
            generate_keypair(private, public, password, purpose=AUTHORIZATION_KEY)
            AuditLedger(ledger_path).append("one", {"value": 1})
            with self.assertRaisesRegex(AuthorizationSignatureError, "cannot be used"):
                seal_ledger(ledger_path, root / "audit.seal.json", private, password)


if __name__ == "__main__":
    unittest.main()
