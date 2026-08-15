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
        # Pass the SAME clock used for the expiry decision. Without this, verify()
        # judged validity against an injected `now` while consume() stamped the ledger
        # from wall-clock time - two clocks in one operation, so ledger timestamps
        # could disagree with the validity window that admitted them, and prune
        # decisions would be made against a different clock than expiry decisions.
        consume(clearance["nonce"], clearance["exercise_id"], now=now)
    return clearance


# A clearance expires after CLEARANCE_TTL_SECONDS, so a nonce older than the TTL can
# never be replayed successfully - the expiry check refuses it first. Retaining such
# entries forever grows the ledger without adding protection. Prune with a wide safety
# margin so clock skew or a paused process cannot open a replay window.
NONCE_RETENTION_SECONDS = CLEARANCE_TTL_SECONDS * 24        # 2 hours for a 5-minute TTL
NONCE_LEDGER_MAX_ENTRIES = 10_000                            # hard ceiling, fail closed

# The safety above is a COUPLING between two constants, and nothing enforced it. Proven
# by probe: consuming any nonce prunes entries older than the retention window, after
# which the pruned nonce IS accepted again. That is unreachable today only because a
# clearance expires after 300s and CLEARANCE-EXPIRED is raised before consume() runs.
#
# Lower this retention below the TTL - a one-line edit, no test would have caught it -
# and pruning opens a LIVE replay window while clearances are still valid. An invariant
# that load-bearing must fail loudly at import, not silently at runtime.
if NONCE_RETENTION_SECONDS <= CLEARANCE_TTL_SECONDS:
    raise AssertionError(
        f"nonce retention ({NONCE_RETENTION_SECONDS}s) must exceed the clearance TTL "
        f"({CLEARANCE_TTL_SECONDS}s); otherwise pruning reopens nonces belonging to "
        "clearances that are still valid, defeating replay protection")


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

    AUD-02: the read-modify-write was unlocked and used a shared `.tmp` sibling.
    A barrier-synchronised 6-process test failed 12/12 rounds with THREE processes
    each consuming the same nonce - replay protection did not hold at all. The whole
    critical section is now under an exclusive lock, and the write is atomic via a
    unique temp file.

    PRODUCTION NOTE: this ledger is machine-local and gitignored. Replay protection
    is per host; cross-host protection needs a shared transactional store and is a
    deployment decision (EXERCISE-CLEARANCE-BINDING-001 limitations).
    """
    from filelock import atomic_write, exclusive_lock

    now = now or datetime.now(UTC)
    try:
        _consume_locked(nonce, exercise_id, now, exclusive_lock, atomic_write)
    except ClearanceError:
        raise                                   # already a typed refusal; do not re-wrap
    except (OSError, TimeoutError) as exc:
        # SELF-FOUND while attacking this fix. Squatting the sibling lock path (e.g.
        # creating `used_nonces.json.lock` as a DIRECTORY) made consume() raise a raw
        # PermissionError, and lock starvation raises a raw TimeoutError. Both escape
        # the typed-refusal contract every caller relies on to fail closed - the same
        # defect class as AUD-05 and AUD-06.
        #
        # Still fails closed either way: no nonce is recorded and no exercise proceeds.
        # But an untyped exception is not an auditable refusal, and a caller catching
        # ClearanceError would not catch it.
        raise ClearanceError(
            "REFUSED [CLEARANCE-LEDGER-UNAVAILABLE] the nonce ledger could not be "
            f"locked or written ({type(exc).__name__}); replay protection cannot be "
            "established, so execution is refused") from exc


def _consume_locked(nonce, exercise_id, now, exclusive_lock, atomic_write) -> None:
    """The locked critical section. Split out so `consume` can translate lock and
    filesystem failures into typed refusals without wrapping its own refusals."""
    with exclusive_lock(NONCE_LEDGER):
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
        if not isinstance(used, dict):
            raise ClearanceError(
                "REFUSED [CLEARANCE-LEDGER-CORRUPT] nonce ledger is not an object")

        if nonce in used:
            raise ClearanceError(
                f"REFUSED [CLEARANCE-REPLAY] nonce already used at {used[nonce]['at']}")

        used = _prune(used, now)
        if len(used) >= NONCE_LEDGER_MAX_ENTRIES:
            raise ClearanceError(
                f"REFUSED [CLEARANCE-LEDGER-FULL] {len(used)} live nonces exceeds the "
                f"{NONCE_LEDGER_MAX_ENTRIES} ceiling; investigate before continuing")

        used[nonce] = {"exercise_id": exercise_id, "at": now.isoformat()}
        atomic_write(NONCE_LEDGER, json.dumps(used, indent=2, sort_keys=True))
