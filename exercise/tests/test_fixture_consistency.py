"""AUD-07 regression: fixture trust material must be self-consistent, not merely present.

Two real defects were reproduced before the fix:

  1. `main(--force)` - the DOCUMENTED regeneration command - rotated the fixture keys
     but never re-signed the engineering scaffolding, so running it silently broke the
     rehearsal with a misleading "authorization signature is invalid".
  2. `material_present()` checked only that files EXIST. A mismatched keypair (private
     key rotated, public record kept) passed, and `ensure()` repaired nothing.

These tests operate on real key material and real signatures. A mocked signature check
would pass regardless of whether the fix works, which is the failure mode being guarded
against.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path

EXERCISE = Path(__file__).resolve().parents[1]
FIXTURES = EXERCISE / "tests" / "fixtures"
sys.path.insert(0, str(EXERCISE))
sys.path.insert(0, str(FIXTURES))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import make_fixture_trust as fixture  # noqa: E402
import run_rehearsal  # noqa: E402


class FixtureConsistencyTests(unittest.TestCase):
    def tearDown(self) -> None:
        # Always leave the tree in a working state for subsequent tests.
        fixture.ensure()

    def _authorization(self) -> dict:
        return json.loads(
            (EXERCISE / "white" / "authorization.json").read_text(encoding="utf-8"))

    def test_force_regeneration_leaves_usable_scaffolding(self) -> None:
        """The documented `--force` command must not leave stale signatures behind."""
        result = subprocess.run(
            [sys.executable, str(FIXTURES / "make_fixture_trust.py"), "--force"],
            capture_output=True, text=True, check=True)
        self.assertIn("re-signed engineering scaffolding", result.stdout)
        # The real assertion: the rehearsal's own verifier accepts the result.
        run_rehearsal.verify_authorization(self._authorization(), allow_fixtures=True)

    def test_mismatched_keypair_is_detected(self) -> None:
        """A private key that does not derive its public record must fail consistency."""
        self.assertTrue(fixture.material_consistent(), "precondition: material is consistent")
        private = json.loads(fixture.PRIVATE.read_text(encoding="utf-8"))
        private["keys"]["fixture-white-2026"] = base64.b64encode(
            Ed25519PrivateKey.generate().private_bytes_raw()).decode()
        fixture.PRIVATE.write_text(json.dumps(private, indent=2), encoding="utf-8")

        self.assertTrue(fixture.material_present(),
                        "all files still exist - existence alone must not imply consistency")
        self.assertFalse(fixture.material_consistent(),
                         "a mismatched keypair must be detected")

    def test_ensure_repairs_mismatched_keypair(self) -> None:
        """Detection without repair would still leave the tree unusable."""
        private = json.loads(fixture.PRIVATE.read_text(encoding="utf-8"))
        private["keys"]["fixture-white-2026"] = base64.b64encode(
            Ed25519PrivateKey.generate().private_bytes_raw()).decode()
        fixture.PRIVATE.write_text(json.dumps(private, indent=2), encoding="utf-8")

        fixture.ensure()

        self.assertTrue(fixture.material_consistent())
        self.assertTrue(fixture.scaffolding_current())
        run_rehearsal.verify_authorization(self._authorization(), allow_fixtures=True)

    def test_ensure_repairs_stale_scaffolding_without_rotating_keys(self) -> None:
        """Keys intact but scaffolding stale: re-sign, do not needlessly rotate keys."""
        before = json.loads(fixture.PRIVATE.read_text(encoding="utf-8"))["keys"]
        path = EXERCISE / "white" / "authorization.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["signature"] = base64.b64encode(b"\x00" * 64).decode()
        path.write_text(json.dumps(document, indent=2), encoding="utf-8")

        self.assertTrue(fixture.material_consistent(), "keys themselves are untouched")
        self.assertFalse(fixture.scaffolding_current(), "scaffolding must be seen as stale")

        fixture.ensure()

        self.assertTrue(fixture.scaffolding_current())
        after = json.loads(fixture.PRIVATE.read_text(encoding="utf-8"))["keys"]
        self.assertEqual(before, after, "stale scaffolding must not force a key rotation")
        run_rehearsal.verify_authorization(self._authorization(), allow_fixtures=True)

    def test_corrupt_private_key_file_is_not_treated_as_consistent(self) -> None:
        """Fail closed on unreadable material rather than raising from deep in a verifier."""
        original = fixture.PRIVATE.read_text(encoding="utf-8")
        try:
            fixture.PRIVATE.write_text("{ not json", encoding="utf-8")
            self.assertFalse(fixture.material_consistent())
            self.assertFalse(fixture.scaffolding_current())
        finally:
            fixture.PRIVATE.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
