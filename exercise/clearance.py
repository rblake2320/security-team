#!/usr/bin/env python3
"""Short-lived, signed preflight clearance. Closes the preflight bypass.

Without this, `preflight.py -> run_rehearsal.py` is advisory: anyone can invoke the
runner directly. The runner now refuses to act without a valid clearance that it
verifies INDEPENDENTLY.

The clearance binds eleven things, so a clearance issued for one situation cannot
be replayed into another:

    exercise_id · mode · authorization receipt digest · manifest digest ·
    approved scope/techniques · authorization expiry · revocation-list digest ·
    safety-boundary config digest · issued_at + expires_at · nonce · runner identity

TRUST STORES ARE SEPARATE. Formal mode loads production keys only. Fixture keys are
marked environment=TEST_ONLY and can never satisfy a production gate.

LIMITATION (stated, not hidden): this defends against accidental bypass, replay, and
modified inputs. It does NOT defend against an attacker with host-level access to the
clearance signing key. That is deployment custody - readiness gate
'key_custody_verified', trust model sec 20.4.

Claim: EXERCISE-CLEARANCE-BINDING-001
Evidence: exercise/tests/test_clearance.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

HERE = Path(__file__).resolve().parent
PROD_TRUST = HERE / "config" / "trust" / "production"
FIXTURE_TRUST = HERE / "tests" / "fixtures" / "trust"
NONCE_LEDGER = HERE / "evidence" / "used_nonces.json"

CLEARANCE_TTL_SECONDS = 300          # short-lived by design
CLEARANCE_SCHEMA = "exercise.preflight-clearance/1.0"
DOMAIN = b"exercise.preflight-clearance.v1"


class ClearanceError(Exception):
    """Clearance refusal. Fail closed."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


# --------------------------------------------------------------------------
# Trust stores
# --------------------------------------------------------------------------

def load_trust_store(mode: str, allow_fixtures: bool | None = None) -> dict[str, dict]:
    """Formal mode loads ONLY the production store. Engineering mode may load fixtures.

    A valid signature from an unknown key is unauthorized: a signature proves a private
    key signed bytes, not that the signer is White/CISO. Identity comes from this registry.
    """
    formal = mode == "FORMAL_INTEGRATED_ASSESSMENT"
    if allow_fixtures is None:
        allow_fixtures = not formal
    if formal and allow_fixtures:
        raise ClearanceError("REFUSED [TRUST-STORE] formal mode may not load fixture keys")

    store: dict[str, dict] = {}
    for base, env in ((PROD_TRUST, "PRODUCTION"), (FIXTURE_TRUST, "TEST_ONLY")):
        if env == "TEST_ONLY" and not allow_fixtures:
            continue
        if not base.exists():
            continue
        for f in sorted(base.glob("*.json")):
            if f.name.startswith("_"):          # fixture private keys are never trust records
                continue
            rec = json.loads(f.read_text(encoding="utf-8"))
            if "key_id" not in rec:             # store README / manifest, not a key
                continue
            if env == "PRODUCTION" and rec.get("environment") == "TEST_ONLY":
                raise ClearanceError(
                    f"REFUSED [TRUST-STORE] TEST_ONLY key {rec.get('key_id')} found in the production store")
            rec["environment"] = rec.get("environment", env)
            store[rec["key_id"]] = rec
    return store


def resolve_key(
    key_id: str,
    store: dict[str, dict],
    mode: str,
    *,
    expected_roles: set[str] | None = None,
) -> Ed25519PublicKey:
    rec = store.get(key_id)
    if rec is None:
        raise ClearanceError(f"REFUSED [UNKNOWN-KEY] {key_id} is not in the trust registry")
    if mode == "FORMAL_INTEGRATED_ASSESSMENT" and rec["environment"] == "TEST_ONLY":
        raise ClearanceError(f"REFUSED [TEST-KEY-IN-FORMAL] {key_id} is TEST_ONLY")
    if expected_roles is not None and rec.get("role") not in expected_roles:
        raise ClearanceError(
            f"REFUSED [KEY-ROLE] {key_id} role {rec.get('role')!r} not in {sorted(expected_roles)}"
        )
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(rec["public_key"]))


# --------------------------------------------------------------------------
# Issue
# --------------------------------------------------------------------------

def issue(*, exercise_id: str, mode: str, authorization: dict, manifest_paths: list[Path],
          scope: list[str], signing_key: Ed25519PrivateKey, signing_key_id: str,
          runner_identity: str, now: datetime | None = None,
          revocations_path: Path | None = None,
          boundaries_path: Path | None = None) -> dict:
    now = now or datetime.now(UTC)
    body = {
        "schema": CLEARANCE_SCHEMA,
        "exercise_id": exercise_id,
        "mode": mode,
        "authorization_digest": digest(authorization),
        "authorization_expires_at": authorization["expires_at"],
        "manifest_digest": digest([file_digest(p) for p in manifest_paths]),
        "approved_scope": sorted(scope),
        "revocation_list_digest": file_digest(revocations_path or (HERE / "config" / "revocations.json")),
        "safety_boundary_digest": file_digest(boundaries_path or (HERE / "config" / "safety_boundaries.json")),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=CLEARANCE_TTL_SECONDS)).isoformat(),
        "nonce": secrets.token_hex(16),
        "runner_identity": runner_identity,
        "signing_key_id": signing_key_id,
    }
    sig = signing_key.sign(DOMAIN + canonical(body))
    return {**body, "signature": base64.b64encode(sig).decode()}


# --------------------------------------------------------------------------
# Verify - performed INDEPENDENTLY by the runner
# --------------------------------------------------------------------------

def verify(clearance: dict, *, exercise_id: str, mode: str, authorization: dict,
           manifest_paths: list[Path], runner_identity: str,
           now: datetime | None = None, consume_nonce: bool = True,
           allow_fixtures: bool | None = None,
           revocations_path: Path | None = None,
           boundaries_path: Path | None = None) -> dict:
    now = now or datetime.now(UTC)

    if clearance.get("schema") != CLEARANCE_SCHEMA:
        raise ClearanceError("REFUSED [CLEARANCE-SCHEMA] unexpected schema")

    store = load_trust_store(mode, allow_fixtures)
    pub = resolve_key(
        clearance.get("signing_key_id", ""),
        store,
        mode,
        expected_roles={"preflight clearance issuer", "clearance_issuer"},
    )

    body = {k: v for k, v in clearance.items() if k != "signature"}
    try:
        pub.verify(base64.b64decode(clearance["signature"]), DOMAIN + canonical(body))
    except InvalidSignature as exc:                      # specific, not broad
        raise ClearanceError("REFUSED [CLEARANCE-SIGNATURE] invalid signature") from exc

    def need(field, actual, expected):
        if actual != expected:
            raise ClearanceError(f"REFUSED [{field}] clearance {actual!r} != actual {expected!r}")

    need("CLEARANCE-EXERCISE", clearance["exercise_id"], exercise_id)
    need("CLEARANCE-MODE", clearance["mode"], mode)
    need("CLEARANCE-RUNNER", clearance["runner_identity"], runner_identity)
    need("CLEARANCE-AUTHORIZATION", clearance["authorization_digest"], digest(authorization))
    need("CLEARANCE-AUTH-EXPIRY", clearance["authorization_expires_at"], authorization["expires_at"])
    need("CLEARANCE-MANIFEST", clearance["manifest_digest"],
         digest([file_digest(p) for p in manifest_paths]))
    need("CLEARANCE-REVOCATIONS", clearance["revocation_list_digest"],
         file_digest(revocations_path or (HERE / "config" / "revocations.json")))
    need("CLEARANCE-BOUNDARIES", clearance["safety_boundary_digest"],
         file_digest(boundaries_path or (HERE / "config" / "safety_boundaries.json")))

    issued = datetime.fromisoformat(clearance["issued_at"])
    expires = datetime.fromisoformat(clearance["expires_at"])
    if not issued <= now <= expires:
        raise ClearanceError(f"REFUSED [CLEARANCE-EXPIRED] valid {issued} to {expires}, now {now}")

    if consume_nonce:
        consume(clearance["nonce"], clearance["exercise_id"])
    return clearance


# A clearance expires after CLEARANCE_TTL_SECONDS, so a nonce older than the TTL can
# never be replayed successfully - the expiry check refuses it first. Retaining such
# entries forever grows the ledger without adding protection. Prune with a wide safety
# margin so clock skew or a paused process cannot open a replay window.
NONCE_RETENTION_SECONDS = CLEARANCE_TTL_SECONDS * 24        # 2 hours for a 5-minute TTL
NONCE_LEDGER_MAX_ENTRIES = 10_000                            # hard ceiling, fail closed


def _prune(used: dict, now: datetime) -> dict:
    """Drop entries older than the retention window. Unparsable entries are KEPT:
    an entry we cannot age out is never silently discarded."""
    kept = {}
    for nonce, rec in used.items():
        try:
            seen = datetime.fromisoformat(rec["at"])
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=UTC)
        except (KeyError, TypeError, ValueError):
            kept[nonce] = rec           # unparsable -> retain, never discard
            continue
        if (now - seen).total_seconds() <= NONCE_RETENTION_SECONDS:
            kept[nonce] = rec
    return kept


def consume(nonce: str, exercise_id: str, *, now: datetime | None = None) -> None:
    """Single use. A replayed clearance is refused even if everything else holds.

    PRODUCTION NOTE: this ledger is machine-local and gitignored. On a fresh clone it
    starts empty, so replay protection is per-host. That is correct for the clearance
    TTL (5 minutes) but means a clearance cannot be replayed on host A and blocked on
    host B. Cross-host replay protection requires a shared ledger and is a deployment
    decision, recorded as a limitation on EXERCISE-CLEARANCE-BINDING-001.
    """
    now = now or datetime.now(UTC)
    used = {}
    if NONCE_LEDGER.exists():
        try:
            used = json.loads(NONCE_LEDGER.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # A corrupt ledger cannot prove non-replay. Fail closed rather than
            # starting fresh, which would silently reopen every past nonce.
            raise ClearanceError(
                "REFUSED [CLEARANCE-LEDGER-CORRUPT] nonce ledger is unreadable; "
                "replay protection cannot be established") from exc

    if nonce in used:
        raise ClearanceError(f"REFUSED [CLEARANCE-REPLAY] nonce already used at {used[nonce]['at']}")

    used = _prune(used, now)
    if len(used) >= NONCE_LEDGER_MAX_ENTRIES:
        raise ClearanceError(
            f"REFUSED [CLEARANCE-LEDGER-FULL] {len(used)} live nonces exceeds the "
            f"{NONCE_LEDGER_MAX_ENTRIES} ceiling; investigate before continuing")

    used[nonce] = {"exercise_id": exercise_id, "at": now.isoformat()}
    NONCE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = NONCE_LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(used, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, NONCE_LEDGER)
