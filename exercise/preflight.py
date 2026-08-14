#!/usr/bin/env python3
"""Exercise preflight gate. Refuses to start an exercise that is not permitted.

    python exercise/preflight.py                 # gate the default rehearsal
    python exercise/preflight.py --mode FORMAL_INTEGRATED_ASSESSMENT

Exit 0 = cleared to run. Exit 1 = REFUSED.

Sits in front of run_rehearsal.py. Reuses its Ed25519 authorization verification
and adds the three things it does not cover:

  1. MODE GATING      - FORMAL_INTEGRATED_ASSESSMENT is refused while any readiness
                        gate is false. This is the mechanism behind the readiness
                        policy; without it the policy is a document.
  2. REVOCATION       - an active revocation refuses execution even when the
                        authorization signature is valid and unexpired.
  3. SAFETY BOUNDARIES- all eleven enforced explicitly, each with its own refusal.

Claim: EXERCISE-PREFLIGHT-REFUSAL-001
Evidence: exercise/tests/test_preflight.py (one negative test per refusal path)
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cryptography.exceptions import InvalidSignature
from run_rehearsal import (
    canonical,
    verify_authorization,  # reuse: signature, expiry, scope
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
READINESS = ROOT / "00-shared" / "config" / "assessment_readiness.json"
MODES = HERE / "config" / "execution_modes.json"
BOUNDARIES = HERE / "config" / "safety_boundaries.json"
REVOCATIONS = HERE / "config" / "revocations.json"


class Refused(Exception):
    """Preflight refusal. Carries the rule that refused, for the evidence record."""

    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"{rule}: {detail}")
        self.rule = rule
        self.detail = detail


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_gates(readiness: dict | None = None) -> list[str]:
    r = readiness or _load(READINESS)
    defs = r["gate_definitions"]
    return [g for g in r["assessment_readiness"]["required_gates"]
            if defs[g]["status"] != "VERIFIED"]


def check_mode(authorization: dict, requested: str, gates: list[str], modes: dict) -> dict:
    """MODE GATING. Formal assessment requires every readiness gate to be true."""
    spec = modes["modes"].get(requested)
    if spec is None:
        raise Refused("MODE-UNKNOWN", f"{requested} is not a defined execution mode")
    if authorization.get("mode") != requested:
        raise Refused("MODE-MISMATCH",
                      f"authorization is for {authorization.get('mode')}, requested {requested}")
    if spec["requires_all_readiness_gates"] and gates:
        raise Refused("MODE-NOT-READY",
                      f"{requested} requires all readiness gates; pending: {', '.join(gates)}")
    if spec["exercise_assurance_required"] and "exercise_assurance_operational" in gates:
        raise Refused("MODE-NO-ASSURANCE",
                      f"{requested} requires an operational Exercise Assurance performer")
    return spec


def check_revocation(authorization: dict, revocations: dict, now: datetime) -> None:
    """REVOCATION. A valid signature is not sufficient; revocation overrides it.

    AUD-06: malformed records previously surfaced KeyError / ValueError /
    AttributeError instead of a named safety refusal. A revocation list that
    cannot be parsed cannot establish that execution is permitted, so every
    malformed record now fails CLOSED under REVOCATION-CONFIG rather than
    escaping as an untyped parser error.
    """
    records = revocations.get("revocations", [])
    if not isinstance(records, list):
        raise Refused("REVOCATION-CONFIG", "revocations must be a list")

    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise Refused("REVOCATION-CONFIG",
                          f"record {index} is not an object; cannot establish revocation state")
        for field in ("revocation_id", "exercise_id", "effective_from", "reason"):
            value = rec.get(field)
            if not isinstance(value, str) or not value.strip():
                raise Refused("REVOCATION-CONFIG",
                              f"record {index} is missing a valid {field!r}")

        if rec["exercise_id"] not in (authorization.get("exercise_id"), "*"):
            continue
        if rec.get("key_id") not in (authorization.get("key_id"), None, "*"):
            continue

        try:
            effective = datetime.fromisoformat(rec["effective_from"])
        except ValueError as exc:
            raise Refused("REVOCATION-CONFIG",
                          f"record {rec['revocation_id']} has an unparseable "
                          f"effective_from: {rec['effective_from']!r}") from exc
        if effective.tzinfo is None:
            # A naive timestamp is ambiguous. Guessing a zone here could place a
            # live revocation in the future and let execution proceed.
            raise Refused("REVOCATION-CONFIG",
                          f"record {rec['revocation_id']} effective_from has no time zone; "
                          "an ambiguous revocation time cannot be evaluated safely")

        if now >= effective:
            raise Refused("REVOKED",
                          f"{rec['revocation_id']} effective {rec['effective_from']}: {rec['reason']}")


def check_boundaries(attestation: dict, boundaries: dict) -> list[str]:
    """SAFETY BOUNDARIES. Each is a separate refusal so the reason is unambiguous.

    Read from a SEPARATE environment attestation, not from the authorization.
    purple.rehearsal-authorization/1.0 uses an exact field-set match, so boundary
    fields cannot be added to it without a schema bump and White re-signature. That
    constraint is correct: the authorization is White's GRANT; the environment
    attestation is a distinct statement about the range the grant applies to.
    """
    satisfied = []
    for b in boundaries["boundaries"]:
        key, expected = b["authorization_field"], b["required_value"]
        actual = attestation.get(key)
        if expected == "__non_empty__":
            ok = bool(actual)
        else:
            ok = actual == expected
        if not ok:
            raise Refused(b["id"], f"{key}={actual!r}, required {expected!r} - {b['boundary']}")
        satisfied.append(b["id"])
    return satisfied


def verify_environment_attestation(
    attestation: dict, *, mode: str, exercise_id: str, allow_fixtures: bool | None = None
) -> None:
    """Verify White's domain-separated statement about the eleven safety boundaries."""
    import clearance as clr

    if attestation.get("schema") != "exercise.environment-attestation/2.0":
        raise Refused("SB-ATTESTATION-SCHEMA", "unsupported environment attestation schema")
    if attestation.get("exercise_id") != exercise_id:
        raise Refused("SB-ATTESTATION-MISMATCH", "environment attestation is for another exercise")
    store = clr.load_trust_store(mode, allow_fixtures)
    record = store.get(attestation.get("attested_by"))
    if record is None:
        raise Refused("SB-ATTESTATION-KEY", "environment attestation signer is not enrolled")
    role_ok = (
        record.get("role") == "white_ciso"
        if mode == "FORMAL_INTEGRATED_ASSESSMENT"
        else record.get("role") in {"White approval authority", "white_ciso"}
    )
    if not role_ok:
        raise Refused("SB-ATTESTATION-ROLE", "environment attestation signer role is not permitted")
    if mode == "FORMAL_INTEGRATED_ASSESSMENT" and attestation.get("environment") == "TEST_ONLY":
        raise Refused("SB-TEST-ATTESTATION-IN-FORMAL", "formal mode refuses TEST_ONLY attestations")
    body = {key: value for key, value in attestation.items() if key != "signature"}
    try:
        public = clr.resolve_key(
            attestation["attested_by"],
            store,
            mode,
            expected_roles={"White approval authority", "white_ciso"},
        )
        public.verify(
            base64.b64decode(attestation["signature"], validate=True),
            b"exercise.environment-attestation.v2" + canonical(body),
        )
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise Refused("SB-ATTESTATION-SIGNATURE", "environment attestation signature is invalid") from exc


def preflight(requested_mode: str = "ENGINEERING_REHEARSAL",
              authorization_path: Path | None = None,
              now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    auth = _load(authorization_path or (HERE / "white" / "authorization.json"))

    verify_authorization(auth, now=now)                    # signature, expiry, scope
    gates = failed_gates()
    spec = check_mode(auth, requested_mode, gates, _load(MODES))
    check_revocation(auth, _load(REVOCATIONS), now)

    att_path = HERE / "white" / "environment_attestation.json"
    if not att_path.exists():
        raise Refused("SB-MISSING-ATTESTATION",
                      "no signed environment attestation; the 11 safety boundaries are unattested")
    attestation = _load(att_path)
    verify_environment_attestation(attestation, mode=requested_mode, exercise_id=auth["exercise_id"])
    satisfied = check_boundaries(attestation, _load(BOUNDARIES))

    return {
        "schema": "exercise.preflight-decision/1.0",
        "decision": "CLEARED",
        "exercise_id": auth["exercise_id"],
        "mode": requested_mode,
        "result_marking": spec["result_marking"],
        "assurance_statement_allowed": spec["assurance_statement_allowed"],
        "readiness_gates_pending": gates,
        "boundaries_satisfied": satisfied,
        "checked_at": now.isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="ENGINEERING_REHEARSAL")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--issue", action="store_true",
                    help="write a short-lived signed clearance the runner will accept")
    a = ap.parse_args()
    try:
        d = preflight(a.mode)
        if a.issue:
            d["clearance_written_to"] = str(_issue_clearance(a.mode))
    except Refused as exc:
        print(f"REFUSED [{exc.rule}] {exc.detail}")
        return 1
    except ValueError as exc:
        print(f"REFUSED [AUTHORIZATION] {exc}")
        return 1
    if a.json:
        print(json.dumps(d, indent=2))
    else:
        print(f"CLEARED  mode={d['mode']}  marking={d['result_marking']}")
        print(f"         boundaries satisfied: {len(d['boundaries_satisfied'])}/11")
        if d["readiness_gates_pending"]:
            print(f"         gates pending: {', '.join(d['readiness_gates_pending'])}")
            print("         assurance statements PROHIBITED")
        if a.issue:
            print(f"         clearance issued -> {d['clearance_written_to']}")
    return 0


def _issue_clearance(mode: str) -> Path:
    """Issue the short-lived clearance the runner requires.

    ENGINEERING_REHEARSAL signs with the TEST_ONLY fixture issuer, because no
    production issuer key is enrolled. FORMAL_INTEGRATED_ASSESSMENT has no issuer at
    all until real authorities enrol, so it refuses here rather than degrading.
    """
    import base64

    import clearance as clr
    import run_rehearsal as rr
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if mode == "FORMAL_INTEGRATED_ASSESSMENT":
        raise Refused("NO-PRODUCTION-ISSUER",
                      "no production clearance-issuer key is enrolled; formal mode cannot be cleared")

    sys.path.insert(0, str(HERE / "tests" / "fixtures"))
    from make_fixture_trust import ensure as ensure_fixture_trust
    ensure_fixture_trust()      # fresh clone: generate TEST_ONLY material on demand
    fixture = HERE / "tests" / "fixtures" / "trust" / "_fixture_private_keys.json"
    if not fixture.exists():
        raise Refused("NO-ISSUER-KEY", "no clearance issuer key available")
    raw = json.loads(fixture.read_text(encoding="utf-8"))["keys"]["fixture-clearance-2026"]
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))

    auth = _load(HERE / "white" / "authorization.json")
    c = clr.issue(exercise_id=auth["exercise_id"], mode=auth["mode"], authorization=auth,
                  manifest_paths=rr.MANIFEST_PATHS, scope=auth["allowed_test_ids"],
                  signing_key=key, signing_key_id="fixture-clearance-2026",
                  runner_identity=rr.RUNNER_IDENTITY)
    out = HERE / "evidence" / "clearance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(c, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
