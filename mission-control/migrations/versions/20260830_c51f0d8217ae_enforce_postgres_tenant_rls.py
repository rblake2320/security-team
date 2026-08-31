"""enforce PostgreSQL tenant row-level security

Revision ID: c51f0d8217ae
Revises: 79ca03174ce6
Create Date: 2026-08-30 21:35:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c51f0d8217ae"
down_revision: Union[str, Sequence[str], None] = "79ca03174ce6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = (
    "agents",
    "ai_assets",
    "ai_policies",
    "ai_usage_events",
    "approvals",
    "assessment_runs",
    "audit_events",
    "connectors",
    "engagement_assets",
    "engagement_targets",
    "engagements",
    "evidence",
    "findings",
    "incidents",
    "invitations",
    "memberships",
    "outbox_events",
    "policy_violations",
    "programs",
    "retention_policies",
    "security_controls",
    "tasks",
    "telemetry_events",
)

LOOKUP_POLICIES = {
    "memberships": "user_id = NULLIF(current_setting('aegis.user_id', true), '')",
    "connectors": "token_prefix = NULLIF(current_setting('aegis.connector_prefix', true), '')",
    "invitations": "token_hash = NULLIF(current_setting('aegis.invitation_digest', true), '')",
}

TENANT_MATCH = "organization_id = NULLIF(current_setting('aegis.organization_id', true), '')"
ORGANIZATION_MATCH = "id = NULLIF(current_setting('aegis.organization_id', true), '')"
ORGANIZATION_BOOTSTRAP = (
    "slug = NULLIF(current_setting('aegis.bootstrap_slug', true), '') OR "
    "EXISTS (SELECT 1 FROM memberships AS aegis_membership "
    "WHERE aegis_membership.organization_id = organizations.id "
    "AND aegis_membership.user_id = NULLIF(current_setting('aegis.user_id', true), ''))"
)
USER_IDENTITY_MATCH = (
    "id = NULLIF(current_setting('aegis.user_id', true), '') OR "
    "email = NULLIF(current_setting('aegis.identity_email', true), '')"
)
USER_TENANT_READ = (
    "EXISTS (SELECT 1 FROM memberships AS aegis_membership "
    "WHERE aegis_membership.user_id = users.id "
    "AND aegis_membership.organization_id = "
    "NULLIF(current_setting('aegis.organization_id', true), ''))"
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY aegis_tenant_scope ON "{table}" '
            f"FOR ALL USING ({TENANT_MATCH}) WITH CHECK ({TENANT_MATCH})"
        )
    for table, expression in LOOKUP_POLICIES.items():
        op.execute(
            f'CREATE POLICY aegis_identity_lookup ON "{table}" '
            f"FOR SELECT USING ({expression})"
        )
    op.execute('ALTER TABLE "organizations" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "organizations" FORCE ROW LEVEL SECURITY')
    op.execute(
        'CREATE POLICY aegis_organization_scope ON "organizations" '
        f"FOR ALL USING ({ORGANIZATION_MATCH}) WITH CHECK ({ORGANIZATION_MATCH})"
    )
    op.execute(
        'CREATE POLICY aegis_organization_bootstrap ON "organizations" '
        f"FOR SELECT USING ({ORGANIZATION_BOOTSTRAP})"
    )
    op.execute('ALTER TABLE "users" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "users" FORCE ROW LEVEL SECURITY')
    op.execute(
        'CREATE POLICY aegis_user_identity_scope ON "users" '
        f"FOR ALL USING ({USER_IDENTITY_MATCH}) WITH CHECK ({USER_IDENTITY_MATCH})"
    )
    op.execute(
        'CREATE POLICY aegis_user_tenant_read ON "users" '
        f"FOR SELECT USING ({USER_TENANT_READ})"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute('DROP POLICY IF EXISTS aegis_user_tenant_read ON "users"')
    op.execute('DROP POLICY IF EXISTS aegis_user_identity_scope ON "users"')
    op.execute('ALTER TABLE "users" NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "users" DISABLE ROW LEVEL SECURITY')
    op.execute('DROP POLICY IF EXISTS aegis_organization_bootstrap ON "organizations"')
    op.execute('DROP POLICY IF EXISTS aegis_organization_scope ON "organizations"')
    op.execute('ALTER TABLE "organizations" NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "organizations" DISABLE ROW LEVEL SECURITY')
    for table in LOOKUP_POLICIES:
        op.execute(f'DROP POLICY IF EXISTS aegis_identity_lookup ON "{table}"')
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS aegis_tenant_scope ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
