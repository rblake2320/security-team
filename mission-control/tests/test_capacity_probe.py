from __future__ import annotations

import asyncio

import httpx
import pytest

from tools.run_capacity_probe import run_profile, validate_profile


def profile() -> dict:
    return {
        "schema": "aegis.capacity-profile/1.0",
        "name": "unit-capacity-contract",
        "requests": 40,
        "concurrency": 8,
        "timeoutSeconds": 2,
        "targets": [
            {"method": "GET", "path": "/api/health", "weight": 3, "expectedStatuses": [200]},
            {"method": "GET", "path": "/api/ready", "weight": 1, "expectedStatuses": [200]},
        ],
        "slo": {"maxErrorRate": 0, "p95Ms": 1000, "p99Ms": 1000},
    }


def test_capacity_probe_emits_passing_commit_bound_receipt(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"path": request.url.path})

    monkeypatch.setenv("AEGIS_COMMIT", "a" * 40)
    receipt = asyncio.run(
        run_profile(
            profile(),
            "http://test",
            {"X-Test-Identity": "secret-value"},
            transport=httpx.MockTransport(handler),
        )
    )
    assert receipt["result"]["passed"] is True
    assert receipt["result"]["failures"] == 0
    assert receipt["buildRevision"] == "a" * 40
    assert receipt["headerNames"] == ["X-Test-Identity"]
    assert "secret-value" not in str(receipt)


def test_capacity_probe_fails_when_a_target_breaks_its_contract():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503 if request.url.path == "/api/ready" else 200)

    receipt = asyncio.run(
        run_profile(profile(), "http://test", transport=httpx.MockTransport(handler))
    )
    assert receipt["result"]["passed"] is False
    assert receipt["result"]["failures"] == 10


def test_capacity_profile_rejects_unbounded_or_missing_work():
    invalid = profile()
    invalid["concurrency"] = 0
    with pytest.raises(ValueError, match="concurrency"):
        validate_profile(invalid)


@pytest.mark.parametrize(
    ("path", "statuses", "timeout", "message"),
    [
        ("//outside.invalid/health", [200], 1, "selected origin"),
        ("/health", [700], 1, "valid HTTP statuses"),
        ("/health", [200], 301, "timeoutSeconds"),
    ],
)
def test_profile_rejects_origin_escape_and_invalid_bounds(path, statuses, timeout, message):
    invalid = profile()
    invalid["targets"][0]["path"] = path
    invalid["targets"][0]["expectedStatuses"] = statuses
    invalid["timeoutSeconds"] = timeout

    with pytest.raises(ValueError, match=message):
        validate_profile(invalid)
