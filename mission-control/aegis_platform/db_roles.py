from __future__ import annotations

import os
import sys

from psycopg import sql
from sqlalchemy import URL, create_engine, make_url


RUNTIME_ROLE = "aegis_runtime"


def _runtime_password() -> str:
    password = os.getenv("AEGIS_DB_RUNTIME_PASSWORD", "")
    if len(password) < 32:
        raise RuntimeError("AEGIS_DB_RUNTIME_PASSWORD must contain at least 32 characters")
    return password


def _admin_url() -> URL:
    raw = os.getenv("DATABASE_ADMIN_URL", "").strip()
    if not raw:
        raise RuntimeError("DATABASE_ADMIN_URL is required")
    parsed = make_url(raw)
    if parsed.get_backend_name() != "postgresql" or not parsed.database:
        raise RuntimeError("DATABASE_ADMIN_URL must target a named PostgreSQL database")
    return parsed


def runtime_url() -> str:
    admin = _admin_url()
    runtime = admin.set(username=RUNTIME_ROLE, password=_runtime_password())
    return runtime.render_as_string(hide_password=False)


def provision_runtime_role() -> None:
    admin = _admin_url()
    password = _runtime_password()
    engine = create_engine(admin, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            driver = connection.connection.driver_connection
            with driver.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (RUNTIME_ROLE,))
                role = sql.Identifier(RUNTIME_ROLE)
                secret = sql.Literal(password)
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL(
                            "CREATE ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER "
                            "NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                        ).format(role, secret)
                    )
                else:
                    cursor.execute(
                        sql.SQL(
                            "ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER "
                            "NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                        ).format(role, secret)
                    )
                database = sql.Identifier(admin.database)
                cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, role))
                cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
                cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(role))
                cursor.execute(
                    sql.SQL(
                        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}"
                    ).format(role)
                )
                cursor.execute(
                    sql.SQL(
                        "GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}"
                    ).format(role)
                )
                cursor.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                    ).format(role)
                )
                cursor.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                        "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}"
                    ).format(role)
                )
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["provision"]:
        provision_runtime_role()
        print("AEGIS_DATABASE_RUNTIME_ROLE=READY")
        return 0
    if arguments == ["runtime-url"]:
        print(runtime_url())
        return 0
    raise RuntimeError("usage: python -m aegis_platform.db_roles provision|runtime-url")


if __name__ == "__main__":
    raise SystemExit(main())
