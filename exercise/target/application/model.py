from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccessResult:
    status: int
    record: dict[str, str] | None
    event: dict[str, Any]


class SyntheticApplication:
    def __init__(self, identities: list[dict[str, str]], records: list[dict[str, str]], *, enforce_scope: bool):
        self.identities = {item["identity_id"]: item for item in identities}
        self.records = {item["record_id"]: item for item in records}
        self.enforce_scope = enforce_scope

    def get_record(self, identity_id: str, record_id: str) -> AccessResult:
        identity = self.identities[identity_id]
        record = self.records[record_id]
        cross_project = identity["project_id"] != record["project_id"]
        allowed = not (self.enforce_scope and cross_project)
        event = {
            "event_type": "record.read",
            "identity_id": identity_id,
            "identity_project": identity["project_id"],
            "record_id": record_id,
            "record_project": record["project_id"],
            "cross_project": cross_project,
            "outcome": "allowed" if allowed else "denied",
        }
        return AccessResult(200 if allowed else 403, record if allowed else None, event)
