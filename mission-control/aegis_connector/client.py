from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import ConnectorConfig


class ConnectorAPIError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class ConnectorAPI:
    def __init__(self, config: ConnectorConfig):
        self.config = config

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/json",
            "User-Agent": "AEGIS-Connector/1.0",
        }
        if self.config.cloudflare_client_id:
            headers["CF-Access-Client-Id"] = self.config.cloudflare_client_id
            headers["CF-Access-Client-Secret"] = self.config.cloudflare_client_secret
        return headers

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        extra_headers: dict[str, str] | None = None,
        expect_bytes: bool = False,
    ) -> Any:
        body = None
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.config.api_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                content = response.read(self.config.max_evidence_bytes + 1 if expect_bytes else 2 * 1024 * 1024)
                if expect_bytes:
                    if len(content) > self.config.max_evidence_bytes:
                        raise ConnectorAPIError(413, "evidence exceeds the connector download limit")
                    return content
                return json.loads(content or b"{}")
        except HTTPError as exc:
            detail = f"Mission Control returned HTTP {exc.code}"
            try:
                parsed = json.loads(exc.read(64_000) or b"{}")
                detail = str(parsed.get("detail") or parsed.get("title") or detail)
            except (ValueError, TypeError):
                pass
            raise ConnectorAPIError(exc.code, detail) from exc
        except URLError as exc:
            raise ConnectorAPIError(0, f"Mission Control is unavailable: {exc.reason}") from exc

    def heartbeat(self, agents: list[dict[str, Any]]) -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/connector/heartbeat",
            {
                "version": "1.0.0",
                "capabilities": ["assessment.execute", "evidence.analyze", "gate.run"],
                "agents": agents,
            },
        )

    def lease(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/connector/tasks/lease")

    def renew(self, task_id: str, lease_token: str) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/connector/tasks/{task_id}/renew",
            {"leaseToken": lease_token},
        )

    def download_evidence(self, task_id: str, lease_token: str) -> bytes:
        return self.request(
            "GET",
            f"/api/v1/connector/tasks/{task_id}/evidence",
            extra_headers={"X-Task-Lease": lease_token},
            expect_bytes=True,
        )

    def complete(
        self,
        task_id: str,
        lease_token: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/v1/connector/tasks/{task_id}/complete",
            {
                "leaseToken": lease_token,
                "status": status,
                "result": result or {},
                "error": (error or "")[:4000] or None,
            },
        )
