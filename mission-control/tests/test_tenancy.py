from __future__ import annotations

import base64
import os
import unittest
from unittest.mock import patch

from sqlalchemy import make_url

from aegis_platform.config import Settings
from aegis_platform.db_roles import runtime_url
from aegis_platform.tenancy import (
    set_bootstrap_slug_context,
    set_connector_lookup_context,
    set_identity_email_context,
    set_invitation_lookup_context,
    set_tenant_context,
    set_user_lookup_context,
)


class _Dialect:
    def __init__(self, name: str):
        self.name = name


class _Bind:
    def __init__(self, dialect: str):
        self.dialect = _Dialect(dialect)


class _Session:
    def __init__(self, dialect: str):
        self.bind = _Bind(dialect)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get_bind(self) -> _Bind:
        return self.bind

    def execute(self, statement, values):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), values))


class TenantContextTests(unittest.TestCase):
    def test_postgres_contexts_are_transaction_local_set_config_calls(self) -> None:
        session = _Session("postgresql")
        set_tenant_context(session, "org-a")  # type: ignore[arg-type]
        set_user_lookup_context(session, "user-a")  # type: ignore[arg-type]
        set_identity_email_context(session, " OWNER@Example.COM ")  # type: ignore[arg-type]
        set_bootstrap_slug_context(session, " Owner-Workspace ")  # type: ignore[arg-type]
        set_connector_lookup_context(session, "aegc_prefix")  # type: ignore[arg-type]
        set_invitation_lookup_context(session, "digest")  # type: ignore[arg-type]
        self.assertEqual(
            [call[1] for call in session.calls],
            [
                {"setting": "aegis.organization_id", "value": "org-a"},
                {"setting": "aegis.user_id", "value": "user-a"},
                {"setting": "aegis.identity_email", "value": "owner@example.com"},
                {"setting": "aegis.bootstrap_slug", "value": "owner-workspace"},
                {"setting": "aegis.connector_prefix", "value": "aegc_prefix"},
                {"setting": "aegis.invitation_digest", "value": "digest"},
            ],
        )
        self.assertTrue(all("set_config" in call[0] for call in session.calls))
        self.assertTrue(all("true" in call[0].lower() for call in session.calls))

    def test_non_postgres_context_is_a_noop(self) -> None:
        session = _Session("sqlite")
        set_tenant_context(session, "org-a")  # type: ignore[arg-type]
        self.assertEqual(session.calls, [])

    def test_runtime_url_uses_restricted_role_and_encodes_password(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_ADMIN_URL": "postgresql+psycopg://admin:admin-pass@db:5432/aegis",
                "AEGIS_DB_RUNTIME_PASSWORD": "runtime/password?with#reserved@characters-12345",
            },
            clear=False,
        ):
            parsed = make_url(runtime_url())
        self.assertEqual(parsed.username, "aegis_runtime")
        self.assertEqual(parsed.password, "runtime/password?with#reserved@characters-12345")
        self.assertEqual(parsed.host, "db")
        self.assertEqual(parsed.database, "aegis")

    def test_runtime_password_must_be_long(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_ADMIN_URL": "postgresql+psycopg://admin:admin-pass@db:5432/aegis",
                "AEGIS_DB_RUNTIME_PASSWORD": "short",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "at least 32"):
                runtime_url()

    def test_production_refuses_database_administrator_as_runtime_identity(self) -> None:
        settings = Settings(
            environment="production",
            database_url="postgresql+psycopg://aegis_admin:password@db:5432/aegis",
            evidence_master_key=base64.urlsafe_b64encode(b"r" * 32).decode().rstrip("="),
            auth_mode="cloudflare",
            cloudflare_team_domain="team.cloudflareaccess.com",
            cloudflare_audience="audience",
            public_hostname="mission.example.com",
            token_pepper="p" * 32,
            bootstrap_email="owner@example.com",
            evidence_scanner_mode="clamav",
            clamav_host="clamav",
        )
        with self.assertRaisesRegex(RuntimeError, "restricted aegis_runtime role"):
            settings.validate()


if __name__ == "__main__":
    unittest.main()
