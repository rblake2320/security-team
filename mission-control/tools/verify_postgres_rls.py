#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from aegis_platform.db_roles import RUNTIME_ROLE, runtime_url
from aegis_platform.models import Connector, Invitation, Membership, Organization, Program, User
from aegis_platform.tenancy import (
    set_bootstrap_slug_context,
    set_connector_lookup_context,
    set_identity_email_context,
    set_invitation_lookup_context,
    set_tenant_context,
    set_user_lookup_context,
)


TENANT_TABLE_COUNT = 25


def _identifier() -> str:
    return str(uuid.uuid4())


def main() -> int:
    if os.getenv("AEGIS_RLS_TEST_MODE") != "confirmed-synthetic-database":
        raise RuntimeError("RLS verification requires an explicitly confirmed synthetic database")
    admin_url = os.environ.get("DATABASE_ADMIN_URL", "")
    if not admin_url or not admin_url.rsplit("/", 1)[-1].split("?", 1)[0].endswith("_rls_test"):
        raise RuntimeError("RLS verification refuses any database not ending in _rls_test")

    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    runtime_engine = create_engine(runtime_url(), pool_pre_ping=True)
    org_a_id = _identifier()
    org_b_id = _identifier()
    user_a_id = _identifier()
    user_b_id = _identifier()
    org_a_slug = f"rls-a-{uuid.uuid4().hex[:8]}"
    user_a_email = f"rls-a-{uuid.uuid4().hex[:8]}@example.test"
    org_a = Organization(id=org_a_id, slug=org_a_slug, name="RLS Tenant A")
    org_b = Organization(id=org_b_id, slug=f"rls-b-{uuid.uuid4().hex[:8]}", name="RLS Tenant B")
    user_a = User(id=user_a_id, email=user_a_email, display_name="RLS A")
    user_b = User(id=user_b_id, email=f"rls-b-{uuid.uuid4().hex[:8]}@example.test", display_name="RLS B")
    prefix_a = "aegc_rls_a_00001"
    prefix_b = "aegc_rls_b_00001"
    digest_a = "a" * 64
    digest_b = "b" * 64

    try:
        with Session(admin_engine) as session, session.begin():
            session.add_all([org_a, org_b, user_a, user_b])
            session.flush()
            session.add_all(
                [
                    Program(organization_id=org_a_id, slug="security", name="Tenant A Program"),
                    Program(organization_id=org_b_id, slug="security", name="Tenant B Program"),
                    Membership(organization_id=org_a_id, user_id=user_a_id, role="viewer"),
                    Membership(organization_id=org_b_id, user_id=user_b_id, role="viewer"),
                    Connector(
                        organization_id=org_a_id,
                        name="Tenant A Connector",
                        token_prefix=prefix_a,
                        token_hash="1" * 64,
                    ),
                    Connector(
                        organization_id=org_b_id,
                        name="Tenant B Connector",
                        token_prefix=prefix_b,
                        token_hash="2" * 64,
                    ),
                    Invitation(
                        organization_id=org_a_id,
                        email=user_a.email,
                        role="viewer",
                        token_hash=digest_a,
                        invited_by_user_id=user_a_id,
                        expires_at=user_a.created_at,
                    ),
                    Invitation(
                        organization_id=org_b_id,
                        email=user_b.email,
                        role="viewer",
                        token_hash=digest_b,
                        invited_by_user_id=user_b_id,
                        expires_at=user_b.created_at,
                    ),
                ]
            )

        with admin_engine.connect() as connection:
            protected = connection.scalar(
                text(
                    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relrowsecurity AND c.relforcerowsecurity"
                )
            )
            role_flags = connection.execute(
                text("SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls FROM pg_roles WHERE rolname = :role"),
                {"role": RUNTIME_ROLE},
            ).one()
        if protected != TENANT_TABLE_COUNT:
            raise RuntimeError(f"expected {TENANT_TABLE_COUNT} forced-RLS tables, received {protected}")
        if any(role_flags):
            raise RuntimeError("runtime role has a privileged PostgreSQL attribute")

        with Session(runtime_engine) as session, session.begin():
            no_context_counts = (
                session.scalar(select(func.count()).select_from(Organization)),
                session.scalar(select(func.count()).select_from(User)),
                session.scalar(select(func.count()).select_from(Program)),
            )
            if no_context_counts != (0, 0, 0):
                raise RuntimeError(f"rows were visible without context: {no_context_counts!r}")

        with Session(runtime_engine) as session, session.begin():
            set_bootstrap_slug_context(session, org_a_slug)
            organizations = list(session.scalars(select(Organization.id)))
            if organizations != [org_a_id]:
                raise RuntimeError("organization bootstrap policy crossed tenant boundaries")

        with Session(runtime_engine) as session, session.begin():
            set_identity_email_context(session, user_a_email)
            users = list(session.scalars(select(User.id)))
            if users != [user_a_id]:
                raise RuntimeError("user identity policy crossed identity boundaries")

        with Session(runtime_engine) as session, session.begin():
            set_tenant_context(session, org_a_id)
            names = list(session.scalars(select(Program.name).order_by(Program.name)))
            if names != ["Tenant A Program"]:
                raise RuntimeError(f"tenant A received unexpected rows: {names!r}")
            session.add(Program(organization_id=org_a_id, slug="allowed-write", name="Tenant A Allowed"))

        denied = False
        try:
            with Session(runtime_engine) as session, session.begin():
                set_tenant_context(session, org_a_id)
                session.add(Program(organization_id=org_b_id, slug="denied-write", name="Tenant B Denied"))
                session.flush()
        except DBAPIError:
            denied = True
        if not denied:
            raise RuntimeError("cross-tenant insert was not denied by PostgreSQL")

        with Session(runtime_engine) as session, session.begin():
            set_user_lookup_context(session, user_a_id)
            memberships = list(session.scalars(select(Membership.organization_id)))
            if memberships != [org_a_id]:
                raise RuntimeError("membership bootstrap policy crossed tenant boundaries")
            organizations = list(session.scalars(select(Organization.id)))
            if organizations != [org_a_id]:
                raise RuntimeError("membership organization policy crossed tenant boundaries")

        with Session(runtime_engine) as session, session.begin():
            set_connector_lookup_context(session, prefix_a)
            connectors = list(session.scalars(select(Connector.organization_id)))
            if connectors != [org_a_id]:
                raise RuntimeError("connector bootstrap policy crossed tenant boundaries")

        with Session(runtime_engine) as session, session.begin():
            set_invitation_lookup_context(session, digest_a)
            invitations = list(session.scalars(select(Invitation.organization_id)))
            if invitations != [org_a_id]:
                raise RuntimeError("invitation bootstrap policy crossed tenant boundaries")

        print("POSTGRES_RUNTIME_ROLE=RESTRICTED")
        print(f"POSTGRES_FORCED_RLS_TABLES={TENANT_TABLE_COUNT}")
        print("POSTGRES_NO_CONTEXT=ZERO_ROWS")
        print("POSTGRES_TENANT_A_ISOLATION=PASS")
        print("POSTGRES_CROSS_TENANT_WRITE=DENIED")
        print("POSTGRES_IDENTITY_BOOTSTRAP=SCOPED")
        return 0
    finally:
        with Session(admin_engine) as session, session.begin():
            session.query(Organization).filter(Organization.id.in_([org_a_id, org_b_id])).delete()
            session.query(User).filter(User.id.in_([user_a_id, user_b_id])).delete()
        runtime_engine.dispose()
        admin_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
