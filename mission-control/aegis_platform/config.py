from __future__ import annotations

import os
import base64
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _integer(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    build_revision: str = "development"
    database_url: str = f"sqlite:///{(PLATFORM_ROOT / 'runtime' / 'platform.db').as_posix()}"
    evidence_root: Path = PLATFORM_ROOT / "runtime" / "evidence"
    evidence_master_key: str = "development-evidence-key-not-production"
    auth_mode: str = "development"
    cloudflare_team_domain: str = ""
    cloudflare_audience: str = ""
    public_hostname: str = ""
    token_pepper: str = "development-only-change-me"
    bootstrap_email: str = "owner@example.test"
    bootstrap_organization: str = "AEGIS Workspace"
    bootstrap_slug: str = "aegis"
    max_event_batch: int = 100
    max_evidence_bytes: int = 10 * 1024 * 1024
    lease_seconds: int = 120
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout_seconds: int = 10
    session_cookie_name: str = "aegis_session"
    evidence_scanner_mode: str = "disabled"
    clamav_host: str = "127.0.0.1"
    clamav_port: int = 3310
    clamav_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            environment=os.getenv("AEGIS_ENV", "development").strip().lower(),
            build_revision=os.getenv("AEGIS_COMMIT", "development").strip().lower(),
            database_url=os.getenv(
                "DATABASE_URL",
                f"sqlite:///{(PLATFORM_ROOT / 'runtime' / 'platform.db').as_posix()}",
            ).strip(),
            evidence_root=Path(
                os.getenv("EVIDENCE_ROOT", str(PLATFORM_ROOT / "runtime" / "evidence"))
            ).resolve(),
            evidence_master_key=os.getenv("EVIDENCE_MASTER_KEY", "development-evidence-key-not-production"),
            auth_mode=os.getenv("AUTH_MODE", "development").strip().lower(),
            cloudflare_team_domain=os.getenv("CF_ACCESS_TEAM_DOMAIN", "").strip().lower(),
            cloudflare_audience=os.getenv("CF_ACCESS_AUD", "").strip(),
            public_hostname=os.getenv("PUBLIC_HOSTNAME", "").strip().lower(),
            token_pepper=os.getenv("TOKEN_PEPPER", "development-only-change-me"),
            bootstrap_email=os.getenv("BOOTSTRAP_EMAIL", "owner@example.test").strip().lower(),
            bootstrap_organization=os.getenv("BOOTSTRAP_ORGANIZATION", "AEGIS Workspace").strip(),
            bootstrap_slug=os.getenv("BOOTSTRAP_SLUG", "aegis").strip().lower(),
            max_event_batch=_integer("MAX_EVENT_BATCH", 100),
            max_evidence_bytes=_integer("MAX_EVIDENCE_BYTES", 10 * 1024 * 1024),
            lease_seconds=_integer("TASK_LEASE_SECONDS", 120),
            database_pool_size=_integer("DB_POOL_SIZE", 5),
            database_max_overflow=_integer("DB_MAX_OVERFLOW", 5),
            database_pool_timeout_seconds=_integer("DB_POOL_TIMEOUT_SECONDS", 10),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "aegis_session").strip(),
            evidence_scanner_mode=os.getenv("EVIDENCE_SCANNER_MODE", "disabled").strip().lower(),
            clamav_host=os.getenv("CLAMAV_HOST", "127.0.0.1").strip().lower(),
            clamav_port=_integer("CLAMAV_PORT", 3310),
            clamav_timeout_seconds=_integer("CLAMAV_TIMEOUT_SECONDS", 30),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment not in {"development", "test", "production"}:
            raise RuntimeError("AEGIS_ENV must be development, test, or production")
        if self.auth_mode not in {"development", "cloudflare"}:
            raise RuntimeError("AUTH_MODE must be development or cloudflare")
        if self.max_event_batch < 1 or self.max_event_batch > 500:
            raise RuntimeError("MAX_EVENT_BATCH must be between 1 and 500")
        if self.max_evidence_bytes < 1024 or self.max_evidence_bytes > 100 * 1024 * 1024:
            raise RuntimeError("MAX_EVIDENCE_BYTES must be between 1 KiB and 100 MiB")
        if self.lease_seconds < 30 or self.lease_seconds > 3600:
            raise RuntimeError("TASK_LEASE_SECONDS must be between 30 and 3600")
        if self.database_pool_size < 1 or self.database_pool_size > 50:
            raise RuntimeError("DB_POOL_SIZE must be between 1 and 50")
        if self.database_max_overflow < 0 or self.database_max_overflow > 100:
            raise RuntimeError("DB_MAX_OVERFLOW must be between 0 and 100")
        if self.database_pool_timeout_seconds < 1 or self.database_pool_timeout_seconds > 60:
            raise RuntimeError("DB_POOL_TIMEOUT_SECONDS must be between 1 and 60")
        if self.evidence_scanner_mode not in {"disabled", "clamav"}:
            raise RuntimeError("EVIDENCE_SCANNER_MODE must be disabled or clamav")
        if not re.fullmatch(r"[a-z0-9.-]{1,253}", self.clamav_host):
            raise RuntimeError("CLAMAV_HOST must be a hostname or IP address")
        if self.clamav_port < 1 or self.clamav_port > 65535:
            raise RuntimeError("CLAMAV_PORT must be between 1 and 65535")
        if self.clamav_timeout_seconds < 1 or self.clamav_timeout_seconds > 300:
            raise RuntimeError("CLAMAV_TIMEOUT_SECONDS must be between 1 and 300")
        if self.environment == "production":
            failures: list[str] = []
            if not re.fullmatch(r"[0-9a-f]{40}", self.build_revision):
                failures.append("AEGIS_COMMIT must be the exact 40-character production revision")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                failures.append("DATABASE_URL must use PostgreSQL")
            elif urlparse(self.database_url).username != "aegis_runtime":
                failures.append("DATABASE_URL must use the restricted aegis_runtime role")
            if self.auth_mode != "cloudflare":
                failures.append("AUTH_MODE must be cloudflare")
            if not self.cloudflare_team_domain or not self.cloudflare_audience:
                failures.append("CF_ACCESS_TEAM_DOMAIN and CF_ACCESS_AUD are required")
            if not self.public_hostname or ":" in self.public_hostname or "/" in self.public_hostname:
                failures.append("PUBLIC_HOSTNAME must be the dedicated application hostname")
            if len(self.token_pepper) < 32 or self.token_pepper == "development-only-change-me":
                failures.append("TOKEN_PEPPER must be a unique secret of at least 32 characters")
            try:
                padded = self.evidence_master_key + "=" * (-len(self.evidence_master_key) % 4)
                evidence_key = base64.urlsafe_b64decode(padded.encode("ascii"))
            except (ValueError, UnicodeError):
                evidence_key = b""
            if len(evidence_key) != 32:
                failures.append("EVIDENCE_MASTER_KEY must be a URL-safe base64-encoded 32-byte key")
            if self.bootstrap_email.endswith("@example.test"):
                failures.append("BOOTSTRAP_EMAIL must name the initial production owner")
            if self.evidence_scanner_mode != "clamav":
                failures.append("EVIDENCE_SCANNER_MODE must be clamav in production")
            if failures:
                raise RuntimeError("Unsafe production configuration: " + "; ".join(failures))
