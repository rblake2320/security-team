from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _set_local(session: Session, setting: str, value: str) -> None:
    """Bind an AEGIS request attribute to the current PostgreSQL transaction."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT set_config(:setting, :value, true)"),
        {"setting": setting, "value": value},
    )


def set_tenant_context(session: Session, organization_id: str) -> None:
    _set_local(session, "aegis.organization_id", organization_id)


def set_user_lookup_context(session: Session, user_id: str) -> None:
    _set_local(session, "aegis.user_id", user_id)


def set_identity_email_context(session: Session, email: str) -> None:
    _set_local(session, "aegis.identity_email", email.strip().lower())


def set_bootstrap_slug_context(session: Session, slug: str) -> None:
    _set_local(session, "aegis.bootstrap_slug", slug.strip().lower())


def set_connector_lookup_context(session: Session, token_prefix: str) -> None:
    _set_local(session, "aegis.connector_prefix", token_prefix)


def set_invitation_lookup_context(session: Session, token_digest: str) -> None:
    _set_local(session, "aegis.invitation_digest", token_digest)
