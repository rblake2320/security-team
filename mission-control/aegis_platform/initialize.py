from __future__ import annotations

from .config import Settings
from .db import Database


def initialize_from_env() -> tuple[str, str]:
    """Run schema/bootstrap once before a multi-worker server starts."""
    settings = Settings.from_env()
    database = Database(settings)
    try:
        if settings.environment != "production":
            database.create_schema()
        return database.bootstrap()
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    initialize_from_env()
