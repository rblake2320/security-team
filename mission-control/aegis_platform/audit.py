from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, Organization, utcnow
from .security import canonical_json, scrub


def canonical_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def append_audit(
    session: Session,
    organization_id: str,
    *,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    organization = session.scalar(
        select(Organization).where(Organization.id == organization_id).with_for_update()
    )
    if not organization:
        raise ValueError("organization not found")
    sequence = organization.audit_seq + 1
    created_at = utcnow()
    clean_detail = scrub(detail or {})
    material = {
        "organization_id": organization_id,
        "sequence": sequence,
        "actor": actor[:320],
        "action": action[:96],
        "target_type": target_type[:64],
        "target_id": target_id[:80],
        "detail": clean_detail,
        "previous_hash": organization.audit_head,
        "created_at": canonical_time(created_at),
    }
    event_hash = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    event = AuditEvent(
        organization_id=organization_id,
        sequence=sequence,
        actor=material["actor"],
        action=material["action"],
        target_type=material["target_type"],
        target_id=material["target_id"],
        detail=clean_detail,
        previous_hash=organization.audit_head,
        event_hash=event_hash,
        created_at=created_at,
    )
    session.add(event)
    organization.audit_seq = sequence
    organization.audit_head = event_hash
    session.flush()
    return event


def verify_audit(session: Session, organization_id: str) -> dict[str, Any]:
    events = list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.sequence)
        )
    )
    previous = "GENESIS"
    for event in events:
        material = {
            "organization_id": organization_id,
            "sequence": event.sequence,
            "actor": event.actor,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "detail": event.detail,
            "previous_hash": event.previous_hash,
            "created_at": canonical_time(event.created_at),
        }
        actual = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
        if event.previous_hash != previous or event.event_hash != actual:
            return {"ok": False, "entries": len(events), "failedAt": event.sequence, "head": previous}
        previous = event.event_hash
    return {"ok": True, "entries": len(events), "head": previous}
