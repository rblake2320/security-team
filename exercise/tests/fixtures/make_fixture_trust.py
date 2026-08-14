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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

TRUST = Path(__file__).resolve().parent / "trust"
PRIVATE = TRUST / "_fixture_private_keys.json"

ROLES = [
    ("fixture-clearance-2026", "preflight clearance issuer"),
    ("fixture-white-2026", "White approval authority"),
    ("fixture-audit-2026", "Internal Audit / Exercise Assurance"),
    ("fixture-sponsor-2026", "Executive sponsor"),
]


def material_present() -> bool:
    return PRIVATE.is_file() and all((TRUST / f"{kid}.json").is_file() for kid, _ in ROLES)


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
    _resign(ex / "white" / "authorization.json", b"", "fixture-white-2026", keys)
    _resign(ex / "white" / "environment_attestation.json",
            b"exercise.environment-attestation.v2", "fixture-white-2026", keys)


def ensure() -> None:
    """Idempotent helper for tests and preflight: generate only if missing."""
    if generate(force=False):
        resign_engineering_artifacts()   # new keys -> scaffolding must be re-signed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if present")
    args = ap.parse_args()
    made = generate(force=args.force)
    print(f"fixture trust material {'generated' if made else 'already present'} -> {TRUST}")
    print("all records marked environment=TEST_ONLY; none are committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
