from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .coverage import seed_security_controls
from .models import AIPolicy, Base, Membership, Organization, Program, RetentionPolicy, User, new_id, utcnow
from .tenancy import set_bootstrap_slug_context, set_identity_email_context, set_tenant_context


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.database_url.startswith("sqlite:///"):
            database_path = settings.database_url.removeprefix("sqlite:///")
            if database_path != ":memory:":
                Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = (
            {"check_same_thread": False, "timeout": 30}
            if settings.database_url.startswith("sqlite")
            else {}
        )
        if settings.database_url.startswith("postgresql"):
            connect_args = {"options": "-c statement_timeout=15000 -c idle_in_transaction_session_timeout=30000"}
        engine_options = {"pool_pre_ping": True, "connect_args": connect_args}
        if settings.database_url.startswith("postgresql"):
            engine_options.update(
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_timeout=settings.database_pool_timeout_seconds,
                pool_recycle=1800,
            )
        self.engine: Engine = create_engine(settings.database_url, **engine_options)
        if settings.database_url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._sqlite_foreign_keys)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False)

    @staticmethod
    def _sqlite_foreign_keys(connection, _record) -> None:  # type: ignore[no-untyped-def]
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def bootstrap(self) -> tuple[str, str]:
        """Create the first owner/workspace idempotently; return user and organization IDs."""
        with self.session() as session:
            if session.get_bind().dialect.name == "postgresql":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": 4_139_447_321_907_111_529},
                )
            set_bootstrap_slug_context(session, self.settings.bootstrap_slug)
            organization = session.scalar(
                select(Organization).where(Organization.slug == self.settings.bootstrap_slug)
            )
            if not organization:
                organization = Organization(
                    id=new_id(),
                    slug=self.settings.bootstrap_slug,
                    name=self.settings.bootstrap_organization,
                )
                set_tenant_context(session, organization.id)
                session.add(organization)
                session.flush()
                session.add(
                    Program(
                        organization_id=organization.id,
                        slug="security",
                        name="AEGIS Security Program",
                        current_state="DESIGN_COMPLETE",
                        configuration={
                            "states": [
                                "DESIGN_COMPLETE",
                                "PREREQUISITES_PENDING",
                                "ASSESSMENT_READY",
                                "EXERCISE_AUTHORIZED",
                                "EXERCISE_COMPLETE",
                                "EVIDENCE_VERIFIED",
                                "ASSESSMENT_ISSUED",
                            ],
                            "teams": ["purple", "white", "yellow", "green", "orange", "blue", "red"],
                        },
                    )
                )
                session.add(RetentionPolicy(organization_id=organization.id))
                session.add(AIPolicy(organization_id=organization.id))

            set_tenant_context(session, organization.id)
            session.flush()
            if not session.scalar(
                select(Program.id).where(Program.organization_id == organization.id).limit(1)
            ):
                session.add(
                    Program(
                        organization_id=organization.id,
                        slug="security",
                        name="AEGIS Security Program",
                        current_state="DESIGN_COMPLETE",
                        configuration={
                            "states": [
                                "DESIGN_COMPLETE",
                                "PREREQUISITES_PENDING",
                                "ASSESSMENT_READY",
                                "EXERCISE_AUTHORIZED",
                                "EXERCISE_COMPLETE",
                                "EVIDENCE_VERIFIED",
                                "ASSESSMENT_ISSUED",
                            ],
                            "teams": ["purple", "white", "yellow", "green", "orange", "blue", "red"],
                        },
                    )
                )
            if not session.get(RetentionPolicy, organization.id):
                session.add(RetentionPolicy(organization_id=organization.id))
            if not session.get(AIPolicy, organization.id):
                session.add(AIPolicy(organization_id=organization.id))
            seed_security_controls(session, organization.id)

            set_identity_email_context(session, self.settings.bootstrap_email)
            user = session.scalar(select(User).where(User.email == self.settings.bootstrap_email))
            if not user:
                user = User(
                    email=self.settings.bootstrap_email,
                    display_name=self.settings.bootstrap_email.split("@", 1)[0],
                )
                session.add(user)
                session.flush()
            membership = session.scalar(
                select(Membership).where(
                    Membership.organization_id == organization.id,
                    Membership.user_id == user.id,
                )
            )
            if not membership:
                session.add(Membership(organization_id=organization.id, user_id=user.id, role="owner"))
            user.last_login_at = utcnow()
            session.flush()
            return user.id, organization.id

    @staticmethod
    def readiness_probe(session: Session) -> None:
        """Prove the active database connection can perform a bounded write round-trip."""
        suffix = " ON COMMIT DELETE ROWS" if session.get_bind().dialect.name == "postgresql" else ""
        session.execute(
            text(
                "CREATE TEMPORARY TABLE IF NOT EXISTS aegis_readiness_probe "
                f"(id INTEGER PRIMARY KEY, value VARCHAR(64) NOT NULL){suffix}"
            )
        )
        token = new_id()
        session.execute(text("DELETE FROM aegis_readiness_probe"))
        session.execute(
            text("INSERT INTO aegis_readiness_probe (id, value) VALUES (1, :value)"),
            {"value": token},
        )
        observed = session.scalar(text("SELECT value FROM aegis_readiness_probe WHERE id = 1"))
        if observed != token:
            raise RuntimeError("database readiness write round-trip failed")
        session.execute(text("DELETE FROM aegis_readiness_probe"))
