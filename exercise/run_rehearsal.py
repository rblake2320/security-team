from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parent
AUTH_FIELDS = {
    "schema", "exercise_id", "mode", "assessment_state", "result_marking", "target",
    "synthetic_data_only", "network_egress", "allowed_test_ids", "valid_from", "expires_at",
    "key_id", "signature",
}

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "target" / "application"))
from model import SyntheticApplication  # noqa: E402

# Inputs bound into the clearance manifest digest. Changing any of them after
# clearance is issued causes the runner to refuse.
MANIFEST_PATHS = [
    ROOT / "target" / "identity-provider" / "identities.json",
    ROOT / "target" / "database" / "records.json",
    ROOT / "orange" / "abuse_cases.json",
    ROOT / "red" / "test_cases.json",
    ROOT / "blue" / "detections.json",
    ROOT / "purple" / "traceability.json",
    ROOT / "green" / "control.json",
    ROOT / "yellow" / "remediation.json",
]


def load(path: Path) -> Any:
    if path.stat().st_size > 1_000_000:
        raise ValueError(f"input is too large: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_authorization(
    document: dict[str, Any], *, now: datetime | None = None, allow_fixtures: bool | None = None
) -> None:
    if set(document) != AUTH_FIELDS or document.get("schema") != "purple.rehearsal-authorization/1.0":
        raise ValueError("authorization fields or schema are invalid")
    mode = document.get("mode")
    mode_fields = {
        "ENGINEERING_REHEARSAL": ("PREREQUISITES_PENDING", "TRAINING_OR_ENGINEERING_USE_ONLY"),
        "FORMAL_INTEGRATED_ASSESSMENT": ("ASSESSMENT_READY", "ASSESSMENT_EVIDENCE"),
    }
    if mode not in mode_fields:
        raise ValueError("authorization execution mode is unsupported")
    expected = {
        "assessment_state": mode_fields[mode][0],
        "result_marking": mode_fields[mode][1],
        "target": "exercise/target",
        "synthetic_data_only": True,
        "network_egress": "blocked",
    }
    if any(document.get(key) != value for key, value in expected.items()):
        raise ValueError("authorization violates a rehearsal safety invariant")
    if document.get("allowed_test_ids") != ["TC-IDOR-001"]:
        raise ValueError("authorization test scope is not exact")
    payload = {key: value for key, value in document.items() if key != "signature"}
    try:
        import clearance as _clr

        store = _clr.load_trust_store(mode, allow_fixtures)
        record = store.get(document["key_id"])
        if record is None:
            raise ValueError("authorization signer is not enrolled")
        accepted_role = (
            record.get("role") == "white_ciso"
            if mode == "FORMAL_INTEGRATED_ASSESSMENT"
            else record.get("role") in {"White approval authority", "white_ciso"}
        )
        if not accepted_role:
            raise ValueError("authorization signer role is not permitted")
        signature = base64.b64decode(document["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key"], validate=True)).verify(
            signature, canonical(payload)
        )
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise ValueError("authorization signature is invalid") from exc
    current = now or datetime.now(UTC)
    start = datetime.fromisoformat(document["valid_from"])
    end = datetime.fromisoformat(document["expires_at"])
    if start.tzinfo is None or end.tzinfo is None or not start <= current <= end:
        raise ValueError("authorization is not currently valid")


RUNNER_IDENTITY = "exercise.run_rehearsal"


def run(
    *,
    write_evidence: bool = True,
    now: datetime | None = None,
    clearance_path: Path | None = None,
    authorization_path: Path | None = None,
    allow_fixtures: bool | None = None,
    revocations_path: Path | None = None,
    boundary_hook: Callable[[str], None] | None = None,
    consume_nonce: bool = True,
) -> dict[str, Any]:
    authorization = load(authorization_path or (ROOT / "white" / "authorization.json"))
    verify_authorization(authorization, now=now, allow_fixtures=allow_fixtures)

    # ENFORCEMENT, not advice. Without a valid short-lived clearance bound to THIS
    # authorization, THIS manifest, THIS mode and THIS runner, execution is refused.
    # Direct invocation of this module therefore cannot bypass preflight.
    import clearance as _clr
    path = clearance_path or (ROOT / "evidence" / "clearance.json")
    if not path.exists():
        raise _clr.ClearanceError(
            "REFUSED [NO-CLEARANCE] run preflight.py first; the runner does not self-authorize")
    _clr.verify(
        load(path),
        exercise_id=authorization["exercise_id"],
        mode=authorization["mode"],
        authorization=authorization,
        manifest_paths=MANIFEST_PATHS,
        runner_identity=RUNNER_IDENTITY,
        now=now,
        allow_fixtures=allow_fixtures,
        revocations_path=revocations_path,
        consume_nonce=consume_nonce,
    )
    _assert_safety_boundary(authorization, "before_baseline", now, revocations_path, boundary_hook)
    identities = load(ROOT / "target" / "identity-provider" / "identities.json")
    records = load(ROOT / "target" / "database" / "records.json")
    abuse_case = load(ROOT / "orange" / "abuse_cases.json")[0]
    test_case = load(ROOT / "red" / "test_cases.json")[0]
    detection = load(ROOT / "blue" / "detections.json")[0]
    trace = load(ROOT / "purple" / "traceability.json")
    if not (
        abuse_case["red_test_id"] == test_case["test_case_id"] == trace["test_case_id"]
        and abuse_case["blue_detection_id"] == detection["detection_id"] == trace["detection_id"]
    ):
        raise ValueError("Orange, Red, Blue, and Purple identifiers are not traceable")

    baseline = SyntheticApplication(identities, records, enforce_scope=False).get_record(
        test_case["identity_id"], test_case["record_id"]
    )
    _assert_safety_boundary(authorization, "after_baseline", now, revocations_path, boundary_hook)
    alert_fired = baseline.event["cross_project"] is True
    _assert_safety_boundary(authorization, "before_retest", now, revocations_path, boundary_hook)
    retest = SyntheticApplication(identities, records, enforce_scope=True).get_record(
        test_case["identity_id"], test_case["record_id"]
    )
    _assert_safety_boundary(authorization, "before_evidence_write", now, revocations_path, boundary_hook)
    stages = {
        "prevented": retest.status == 403,
        "logged": baseline.event["event_type"] == "record.read",
        "alerted": alert_fired,
        "investigated": alert_fired,
        "contained": alert_fired,
        "reported": True,
    }
    result = {
        "schema": "purple.first-run-result/1.0",
        "exercise_id": authorization["exercise_id"],
        "result_marking": authorization["result_marking"],
        "orange_prediction_confirmed": baseline.status == abuse_case["expected_baseline"],
        "baseline_status": baseline.status,
        "retest_status": retest.status,
        "remediation_effective": retest.status == abuse_case["expected_retest"],
        "six_stage_results": stages,
        "all_stages_evidenced": all(stages.values()),
        "network_activity": False,
    }
    if write_evidence:
        output = ROOT / "evidence" / "first_run_results.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        body = canonical(result) + b"\n"
        temporary.write_bytes(body)
        os.replace(temporary, output)
        digest = hashlib.sha256(body).hexdigest()
        print(f"{result['result_marking']}: rehearsal complete; evidence_sha256={digest}")
    return result


def _assert_safety_boundary(
    authorization: dict[str, Any],
    boundary: str,
    now: datetime | None,
    revocations_path: Path | None,
    hook: Callable[[str], None] | None,
) -> None:
    """Re-evaluate authoritative revocation at every material execution boundary."""
    import clearance as clr
    import preflight

    if hook is not None:
        hook(boundary)
    try:
        preflight.check_revocation(
            authorization,
            load(revocations_path or (ROOT / "config" / "revocations.json")),
            now or datetime.now(UTC),
        )
    except preflight.Refused as exc:
        raise clr.ClearanceError(f"REFUSED [{exc.rule}] at safety boundary {boundary}: {exc.detail}") from exc


if __name__ == "__main__":
    import clearance as _clr

    try:
        raise SystemExit(0 if run()["all_stages_evidenced"] else 2)
    except _clr.ClearanceError as exc:      # fail closed, exit 1, no traceback
        print(exc)
        raise SystemExit(1) from None
    except ValueError as exc:
        print(f"REFUSED [AUTHORIZATION] {exc}")
        raise SystemExit(1) from None
