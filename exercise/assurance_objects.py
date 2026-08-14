from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

DOMAINS = {
    "exercise.execution-receipt/1.0": b"exercise.execution-receipt.v1",
    "exercise.assessment-result/1.0": b"exercise.assessment-result.v1",
    "exercise.audit-anchor-receipt/1.0": b"exercise.audit-anchor-receipt.v1",
}
ROLES = {
    "exercise.execution-receipt/1.0": {"red_execution"},
    "exercise.assessment-result/1.0": {
        "exercise_assurance", "internal_audit", "Internal Audit / Exercise Assurance",
    },
    "exercise.audit-anchor-receipt/1.0": {
        "white_evidence", "internal_audit", "Internal Audit / Exercise Assurance",
    },
}
FIELDS = {
    "exercise.execution-receipt/1.0": {
        "schema", "exercise_id", "authorization_sha256", "test_case_ids", "actions_sha256",
        "started_at", "finished_at", "key_id", "signature",
    },
    "exercise.assessment-result/1.0": {
        "schema", "exercise_id", "scorecard_sha256", "evidence_manifest_sha256",
        "evidence_complete", "scores", "result_marking", "issued_at", "key_id", "signature",
    },
    "exercise.audit-anchor-receipt/1.0": {
        "schema", "source", "audit_head", "audit_entries", "previous_receipt_sha256",
        "received_at", "key_id", "signature",
    },
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sign(body: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    schema = body.get("schema")
    if schema not in DOMAINS or "signature" in body or set(body) != FIELDS[schema] - {"signature"}:
        raise ValueError("signed assurance object fields are not exact")
    signature = private_key.sign(DOMAINS[schema] + canonical(body))
    return {**body, "signature": base64.b64encode(signature).decode("ascii")}


def verify(document: dict[str, Any], trust: dict[str, dict[str, Any]]) -> dict[str, Any]:
    schema = document.get("schema")
    if schema not in DOMAINS or set(document) != FIELDS[schema]:
        raise ValueError("signed assurance object fields are not exact")
    record = trust.get(document.get("key_id"))
    if record is None or record.get("status", "active") != "active":
        raise ValueError("assurance-object signer is not actively trusted")
    if record.get("role") not in ROLES[schema]:
        raise ValueError("assurance-object signer role is not permitted")
    body = {key: value for key, value in document.items() if key != "signature"}
    _validate_body(body)
    try:
        public = base64.b64decode(record["public_key"], validate=True)
        signature = base64.b64decode(document["signature"], validate=True)
        if len(public) != 32 or len(signature) != 64:
            raise ValueError
        Ed25519PublicKey.from_public_bytes(public).verify(signature, DOMAINS[schema] + canonical(body))
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise ValueError("assurance-object signature is invalid") from exc
    return body


def validate_rotation_recovery(records: list[dict[str, Any]]) -> None:
    purposes = {"authorization", "execution", "evidence", "assessment", "emergency_revocation"}
    if {record.get("purpose") for record in records} != purposes or len(records) != len(purposes):
        raise ValueError("rotation/recovery requires exactly all five key purposes")
    for record in records:
        expected = {
            "purpose", "old_key_sha256", "new_key_sha256", "recovered_key_sha256",
            "rotated_at", "recovered_at", "holder_unavailable_tested",
        }
        if set(record) != expected:
            raise ValueError("key lifecycle record fields are not exact")
        if not all(_is_hash(record[field]) for field in ("old_key_sha256", "new_key_sha256", "recovered_key_sha256")):
            raise ValueError("key lifecycle fingerprints must be lowercase SHA-256")
        if record["old_key_sha256"] == record["new_key_sha256"]:
            raise ValueError("rotation did not replace the key")
        if record["new_key_sha256"] != record["recovered_key_sha256"]:
            raise ValueError("recovery did not reproduce the current key")
        if record["holder_unavailable_tested"] is not True:
            raise ValueError("holder-unavailable recovery was not exercised")
        if datetime.fromisoformat(record["recovered_at"]) < datetime.fromisoformat(record["rotated_at"]):
            raise ValueError("recovery predates rotation")


def _validate_body(body: dict[str, Any]) -> None:
    for name, value in body.items():
        if name.endswith("_sha256") or name == "audit_head":
            if not _is_hash(value):
                raise ValueError(f"{name} must be lowercase SHA-256")
    if body["schema"] == "exercise.execution-receipt/1.0" and not body["test_case_ids"]:
        raise ValueError("execution receipt requires test cases")
    if body["schema"] == "exercise.assessment-result/1.0" and body["evidence_complete"] is not True:
        raise ValueError("an assessment result cannot be signed with incomplete evidence")
    if body["schema"] == "exercise.audit-anchor-receipt/1.0":
        if type(body["audit_entries"]) is not int or body["audit_entries"] < 1:
            raise ValueError("audit anchor requires a positive entry count")


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
