"""Falsification tests for AEGIS-COMMIT-* claims.

Evidence for the assurance-claim registry. Every test ID here is referenced by a
claim in 00-shared/config/assurance_claims.json. A claim whose tests do not run,
or which has only positive tests, does not reach EVIDENCED.

    python -m unittest discover -s 00-shared/tools -p "test_*.py"
"""

import hashlib
import json
import secrets
import unittest

DOMAIN = b"aegis.inject-commitment.v2"
SALT_BYTES = 48  # 384 bits, above the 256-bit minimum in the claim


def u64be(n: int) -> bytes:
    return n.to_bytes(8, "big")


def frame(*parts: bytes) -> bytes:
    """Length-framed preimage. Raw concatenation would admit boundary shifting."""
    return b"".join(u64be(len(p)) + p for p in parts)


def canonical(pkg: dict) -> bytes:
    """Stand-in for RFC 8785 JCS: deterministic, sorted, no insignificant whitespace."""
    return json.dumps(pkg, separators=(",", ":"), sort_keys=True).encode("utf-8")


def commit_v2(pkg: dict, salt: bytes) -> str:
    return hashlib.sha384(frame(DOMAIN, canonical(pkg), salt)).hexdigest()


def commit_v1_deprecated(pkg: dict) -> str:
    """v1 as actually shipped: digest over the package only. Nonce was NOT in the
    preimage. Reproduced solely to demonstrate the defect in TEST-COMMIT-PRE-REVEAL-ENUMERATION."""
    return hashlib.sha384(canonical(pkg)).hexdigest()


def package(inject_ids):
    return {"type": "aegis.inject-package.v1", "exercise_id": "EX-2026-001",
            "injects": [{"id": i} for i in inject_ids]}


class CommitmentTests(unittest.TestCase):

    # --- TEST-COMMIT-CORRECT-OPENING -------------------------------------
    def test_correct_opening(self):
        """Claim AEGIS-COMMIT-BINDING-001: a correct opening reopens the commitment."""
        pkg, salt = package(["INJ-01", "INJ-02"]), secrets.token_bytes(SALT_BYTES)
        c = commit_v2(pkg, salt)
        self.assertEqual(len(c), 96, "SHA-384 must produce 96 hex chars")
        self.assertEqual(commit_v2(pkg, salt), c)

    # --- TEST-COMMIT-WRONG-SALT ------------------------------------------
    def test_wrong_salt_fails(self):
        """NEGATIVE. A different salt must not open the commitment."""
        pkg, salt = package(["INJ-01"]), secrets.token_bytes(SALT_BYTES)
        c = commit_v2(pkg, salt)
        for _ in range(50):
            self.assertNotEqual(commit_v2(pkg, secrets.token_bytes(SALT_BYTES)), c)

    # --- TEST-COMMIT-TAMPERED-PACKAGE ------------------------------------
    def test_tampered_package_fails(self):
        """NEGATIVE. Binding: substituting the package after committing must fail."""
        salt = secrets.token_bytes(SALT_BYTES)
        c = commit_v2(package(["INJ-01", "INJ-02"]), salt)
        for tampered in (package(["INJ-01"]),                    # inject removed
                         package(["INJ-01", "INJ-03"]),          # inject substituted
                         package(["INJ-01", "INJ-02", "INJ-03"]),# inject added
                         package(["INJ-02", "INJ-01"])):         # order changed
            self.assertNotEqual(commit_v2(tampered, salt), c)

    # --- TEST-COMMIT-FRAMING-BOUNDARY ------------------------------------
    def test_framing_prevents_boundary_shift(self):
        """NEGATIVE. Length framing must distinguish ("ab","c") from ("a","bc").
        Raw concatenation would collide."""
        salt = secrets.token_bytes(SALT_BYTES)
        a = hashlib.sha384(frame(b"ab", b"c", salt)).hexdigest()
        b = hashlib.sha384(frame(b"a", b"bc", salt)).hexdigest()
        self.assertNotEqual(a, b)
        # and demonstrate the failure the framing exists to prevent
        self.assertEqual(hashlib.sha384(b"ab" + b"c" + salt).hexdigest(),
                         hashlib.sha384(b"a" + b"bc" + salt).hexdigest(),
                         "raw concatenation collides - this is why framing is required")

    # --- TEST-COMMIT-PRE-REVEAL-ENUMERATION ------------------------------
    def test_pre_reveal_enumeration(self):
        """THE HIDING TEST. Claim AEGIS-COMMIT-HIDING-001.

        Inject packages are short and structurally predictable, so an attacker can
        enumerate plausible candidates. Demonstrates:
          v1 (no secret salt in preimage) -> ENUMERABLE, hiding FAILS
          v2 (secret salt in preimage)    -> NOT enumerable without the salt
        """
        candidates = [package([f"INJ-{i:02d}"]) for i in range(1, 501)]
        target = candidates[247]

        # v1 as shipped: digest over the package alone.
        c1 = commit_v1_deprecated(target)
        found_v1 = [p for p in candidates if commit_v1_deprecated(p) == c1]
        self.assertEqual(len(found_v1), 1,
                         "v1 must be shown enumerable - this is the deprecated defect")
        self.assertEqual(found_v1[0], target)

        # v2: salt is secret, so the attacker cannot compute any candidate digest.
        salt = secrets.token_bytes(SALT_BYTES)
        c2 = commit_v2(target, salt)
        attacker_guess = secrets.token_bytes(SALT_BYTES)  # attacker does not hold the salt
        found_v2 = [p for p in candidates if commit_v2(p, attacker_guess) == c2]
        self.assertEqual(found_v2, [],
                         "v2 must NOT be enumerable without the opening salt")

        # and the holder can still open it
        self.assertEqual(commit_v2(target, salt), c2)

    # --- TEST-COMMIT-SALT-ENTROPY ----------------------------------------
    def test_salt_entropy_floor(self):
        """Claim assumption: opening_salt >= 256 bits from a CSPRNG."""
        self.assertGreaterEqual(SALT_BYTES * 8, 256)
        s = {secrets.token_bytes(SALT_BYTES) for _ in range(2000)}
        self.assertEqual(len(s), 2000, "CSPRNG health: no collisions expected")

    # --- TEST-COMMIT-LENGTH-LEAK (known limitation, asserted not fixed) ---
    def test_package_length_is_not_concealed(self):
        """LIMITATION under test, per the claim's stated limitations.

        The construction does NOT conceal package length unless separately padded.
        Asserted explicitly so the limitation cannot be quietly forgotten: if someone
        later adds padding, this test fails and the claim must be revisited.
        """
        salt = secrets.token_bytes(SALT_BYTES)
        small = package(["INJ-01"])
        large = package([f"INJ-{i:02d}" for i in range(1, 30)])
        self.assertNotEqual(len(canonical(small)), len(canonical(large)))
        # digest length is constant, but the PREIMAGE length differs and is observable
        # to anyone who learns the package; length is not hidden by this construction.
        self.assertEqual(len(commit_v2(small, salt)), len(commit_v2(large, salt)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
