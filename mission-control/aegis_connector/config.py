from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(os.pathsep) if item.strip())


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _secret(name: str) -> str:
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    secret_file = os.getenv(f"{name}_FILE", "").strip()
    if not secret_file:
        return ""
    path = Path(secret_file).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 16_384:
        raise RuntimeError(f"{name}_FILE must identify a bounded secret file")
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class ConnectorConfig:
    api_url: str
    token: str
    program_root: Path
    allowed_roots: tuple[Path, ...]
    allowed_hosts: tuple[str, ...]
    cloudflare_client_id: str = ""
    cloudflare_client_secret: str = ""
    poll_seconds: int = 10
    request_timeout_seconds: int = 30
    task_timeout_seconds: int = 840
    max_output_chars: int = 24_000
    max_evidence_bytes: int = 10 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "ConnectorConfig":
        program_root = Path(os.getenv("AEGIS_PROGRAM_ROOT", Path.cwd())).resolve()
        configured_roots = _split_list(os.getenv("AEGIS_ALLOWED_ROOTS", str(program_root)))
        allowed_roots = tuple(Path(item).resolve() for item in configured_roots)
        allowed_hosts = tuple(
            sorted(
                {
                    item.strip().lower().rstrip(".")
                    for item in os.getenv("AEGIS_ALLOWED_HOSTS", "").split(",")
                    if item.strip()
                }
            )
        )
        config = cls(
            api_url=os.getenv("AEGIS_API_URL", "http://127.0.0.1:8780").strip().rstrip("/"),
            token=_secret("AEGIS_CONNECTOR_TOKEN"),
            program_root=program_root,
            allowed_roots=allowed_roots,
            allowed_hosts=allowed_hosts,
            cloudflare_client_id=_secret("CF_ACCESS_CLIENT_ID"),
            cloudflare_client_secret=_secret("CF_ACCESS_CLIENT_SECRET"),
            poll_seconds=_integer("AEGIS_POLL_SECONDS", 10, 2, 300),
            request_timeout_seconds=_integer("AEGIS_REQUEST_TIMEOUT_SECONDS", 30, 2, 300),
            task_timeout_seconds=_integer("AEGIS_TASK_TIMEOUT_SECONDS", 840, 30, 3600),
            max_output_chars=_integer("AEGIS_MAX_OUTPUT_CHARS", 24_000, 1_000, 100_000),
            max_evidence_bytes=_integer("AEGIS_MAX_EVIDENCE_BYTES", 10 * 1024 * 1024, 1024, 100 * 1024 * 1024),
        )
        config.validate()
        return config

    def validate(self) -> None:
        parsed = urlsplit(self.api_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise RuntimeError("AEGIS_API_URL must be an http(s) origin without credentials")
        if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("AEGIS_API_URL must use HTTPS unless it is loopback-only")
        if not self.token.startswith("aegc_") or len(self.token) < 24:
            raise RuntimeError("AEGIS_CONNECTOR_TOKEN is missing or invalid")
        if not self.program_root.is_dir():
            raise RuntimeError("AEGIS_PROGRAM_ROOT must be an existing directory")
        if not self.allowed_roots:
            raise RuntimeError("at least one AEGIS_ALLOWED_ROOTS entry is required")
        for root in self.allowed_roots:
            if not root.is_dir():
                raise RuntimeError(f"allowed root does not exist: {root}")
        if bool(self.cloudflare_client_id) != bool(self.cloudflare_client_secret):
            raise RuntimeError("both Cloudflare Access service-token values are required together")

    def resolve_allowed_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser().resolve(strict=True)
        for root in self.allowed_roots:
            if candidate == root or root in candidate.parents:
                return candidate
        raise PermissionError("repository target is outside the connector's local allowlist")

    def assert_allowed_host(self, hostname: str) -> str:
        normalized = hostname.lower().rstrip(".")
        if not normalized or normalized not in self.allowed_hosts:
            raise PermissionError(f"host {normalized or '[missing]'} is not in AEGIS_ALLOWED_HOSTS")
        addresses = {item[4][0] for item in socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)}
        for raw in addresses:
            address = ipaddress.ip_address(raw)
            if not address.is_global:
                raise PermissionError(f"host {normalized} resolved to a non-public address")
        return normalized

    def public_summary(self) -> dict[str, object]:
        return {
            "apiOrigin": self.api_url,
            "programRoot": self.program_root.name,
            "allowedRootCount": len(self.allowed_roots),
            "allowedHosts": list(self.allowed_hosts),
            "cloudflareAccess": bool(self.cloudflare_client_id),
        }
