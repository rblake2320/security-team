#!/usr/bin/env python3
"""Generate the TEST_ONLY fixture trust material.

    python exercise/tests/fixtures/make_fixture_trust.py [--force]

WHY THIS EXISTS
    Fixture PRIVATE keys are gitignored - private keys must never enter git history.
    The fixture PUBLIC records were committed, so a fresh clone had public keys with
    no matching private keys and could not run the exercise rehearsal at all. CI
    found this on the workflow's first real run; local runs never would have, because
    the keys already existed on the developer's disk.

    The fix is reproducibility, not a weaker assertion: fixture trust material is
    GENERATED on demand and none of it is committed. A clean checkout regenerates a
    self-consistent keypair set.

SAFETY
    Every record is marked environment=TEST_ONLY. Formal mode refuses TEST_ONLY keys
    (clearance.load_trust_store / resolve_key), so regenerated fixture keys can never
    satisfy a production gate. The production trust store is separate and empty.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

TRUST = Path(__file__).resolve().parent / "trust"
# (path relative to exercise/, signing domain). One list so the consistency check and
# the re-signer can never drift apart - drift there is exactly how AUD-07 hid.
_SCAFFOLDING = [
    (Path("white") / "authorization.json", b""),
    (Path("white") / "environment_attestation.json", b"exercise.environment-attestation.v2"),
]
PRIVATE = TRUST / "_fixture_private_keys.json"

ROLES = [
    ("fixture-clearance-2026", "preflight clearance issuer"),
    ("fixture-white-2026", "White approval authority"),
    ("fixture-audit-2026", "Internal Audit / Exercise Assurance"),
    ("fixture-sponsor-2026", "Executive sponsor"),
]


def material_present() -> bool:
    """Files exist. NOT sufficient on its own - see `material_consistent`."""
    return PRIVATE.is_file() and all((TRUST / f"{kid}.json").is_file() for kid, _ in ROLES)


def material_consistent() -> bool:
    """Every private key actually derives the public key recorded beside it.

    AUD-07: `material_present` only checked that files EXIST. Existence is not
    consistency. Regenerating private keys while public records survived (or the
    reverse) left a set that looked complete and failed at signature-verification
    time with a misleading "signature is invalid", far from the real cause.

    Derive each public key from its private key and compare. Cheap, and it turns a
    confusing downstream failure into an accurate local one.
    """
    if not material_present():
        return False
    try:
        keys = json.loads(PRIVATE.read_text(encoding="utf-8"))["keys"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False
    for key_id, _role in ROLES:
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(keys[key_id]))
            record = json.loads((TRUST / f"{key_id}.json").read_text(encoding="utf-8"))
            expected = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
            if record.get("public_key") != expected:
                return False
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False
    return True


def scaffolding_current() -> bool:
    """The fixture-signed ENGINEERING scaffolding verifies against the CURRENT keys.

    AUD-07: `main(--force)` regenerated keys but never re-signed, so a developer who
    ran the documented `--force` command silently broke the rehearsal. Verify rather
    than assume.
    """
    try:
        keys = json.loads(PRIVATE.read_text(encoding="utf-8"))["keys"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False
    exercise_root = TRUST.parents[2]
    for relative, domain in _SCAFFOLDING:
        path = exercise_root / relative
        if not path.is_file():
            return False
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            body = {k: v for k, v in doc.items() if k != "signature"}
            payload = json.dumps(body, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode("utf-8")
            private_key = Ed25519PrivateKey.from_private_bytes(
                base64.b64decode(keys["fixture-white-2026"]))
            private_key.public_key().verify(
                base64.b64decode(doc["signature"]), domain + payload)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, InvalidSignature):
            return False
    return True


def generate(force: bool = False) -> bool:
    """Return True if material was generated, False if it already existed."""
    if material_present() and not force:
        return False

    TRUST.mkdir(parents=True, exist_ok=True)
    private: dict[str, str] = {}

    for key_id, role in ROLES:
        key = Ed25519PrivateKey.generate()
        (TRUST / f"{key_id}.json").write_text(json.dumps({
            "key_id": key_id,
            "role": role,
            "environment": "TEST_ONLY",
            "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode(),
            "WARNING": "FIXTURE KEY. Can never satisfy a production gate. "
                       "Formal mode refuses it. Regenerate with make_fixture_trust.py.",
        }, indent=2), encoding="utf-8")
        private[key_id] = base64.b64encode(key.private_bytes_raw()).decode()

    PRIVATE.write_text(json.dumps({
        "WARNING": "FIXTURE PRIVATE KEYS - TEST_ONLY. Never commit. Never use in formal mode.",
        "environment": "TEST_ONLY",
        "keys": private,
    }, indent=2), encoding="utf-8")
    return True


def _resign(path: Path, domain: bytes, signer_key_id: str, keys: dict) -> None:
    """Re-sign a fixture-signed engineering artifact with the CURRENT key."""
    if not path.is_file():
        raise FileNotFoundError(
            f"expected engineering artifact is missing: {path}. Silently skipping it is "
            "how a stale signature survived a regeneration.")
    doc = json.loads(path.read_text(encoding="utf-8"))
    body = {k: v for k, v in doc.items() if k != "signature"}
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(keys[signer_key_id]))
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    doc["signature"] = base64.b64encode(key.sign(domain + payload)).decode()
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def resign_engineering_artifacts() -> None:
    """Re-sign the ENGINEERING-mode scaffolding against current fixture keys.

    exercise/white/authorization.json and environment_attestation.json are signed by
    a TEST_ONLY fixture key. They are scaffolding, not real authorizations, so they
    are regenerated rather than committed - a committed signature bound to generated
    keys breaks on every fresh clone. CI found this on the first real workflow run.
    """
    keys = json.loads(PRIVATE.read_text(encoding="utf-8"))["keys"]
    ex = TRUST.parents[2]                      # .../exercise  (trust->fixtures->tests->exercise)
    for relative, domain in _SCAFFOLDING:
        _resign(ex / relative, domain, "fixture-white-2026", keys)


def ensure() -> None:
    """Idempotent helper for tests and preflight: converge on self-consistent material.

    AUD-07: this previously regenerated only when files were MISSING, and re-signed
    only when it had regenerated. Material that was present but internally
    inconsistent - mismatched keypairs, or scaffolding signed by a superseded key -
    was left in place and surfaced later as a misleading signature failure.

    Now both conditions are checked for real, and each is repaired.
    """
    if not material_consistent():
        generate(force=True)
        resign_engineering_artifacts()
        return
    if not scaffolding_current():
        resign_engineering_artifacts()   # keys fine, scaffolding stale


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if present")
    args = ap.parse_args()
    made = generate(force=args.force)
    if made or not scaffolding_current():
        # AUD-07: --force rotated the keys but left the scaffolding signed by the old
        # one, so the documented regeneration command silently broke the rehearsal.
        resign_engineering_artifacts()
        print("re-signed engineering scaffolding against current fixture keys")
    print(f"fixture trust material {'generated' if made else 'already present'} -> {TRUST}")
    print("all records marked environment=TEST_ONLY; none are committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
