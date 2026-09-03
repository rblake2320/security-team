#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return ordered[index]


class NoRedirectHandler(HTTPRedirectHandler):
    """Keep every load request on the explicitly selected origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def request_once(
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: object | None,
    timeout: float,
) -> int:
    """Execute one bounded request using only the Python standard library."""
    body = None
    request_headers = dict(headers)
    if json_body is not None:
        body = canonical_json(json_body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=body, headers=request_headers, method=method)
    opener = build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            response.read(65_537)
            return response.status
    except HTTPError as exc:
        exc.read(65_537)
        return exc.code


def validate_profile(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("schema") != "aegis.capacity-profile/1.0":
        raise ValueError("capacity profile schema is unsupported")
    requests = int(raw.get("requests", 0))
    concurrency = int(raw.get("concurrency", 0))
    if requests < 1 or requests > 2_000_000:
        raise ValueError("requests must be between 1 and 2000000")
    if concurrency < 1 or concurrency > min(requests, 512):
        raise ValueError("concurrency must be positive and no greater than requests or 512")
    targets = raw.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("at least one capacity target is required")
    for target in targets:
        if target.get("method") not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("capacity target method is unsupported")
        target_path = str(target.get("path", ""))
        target_url = urlsplit(target_path)
        if (
            not target_path.startswith("/")
            or target_path.startswith("//")
            or target_url.scheme
            or target_url.netloc
        ):
            raise ValueError("capacity target path must stay on the selected origin")
        if int(target.get("weight", 0)) < 1 or int(target.get("weight", 0)) > 100:
            raise ValueError("capacity target weight must be between 1 and 100")
        statuses = target.get("expectedStatuses")
        if not isinstance(statuses, list) or not statuses:
            raise ValueError("capacity target expectedStatuses is required")
        if any(int(status) < 100 or int(status) > 599 for status in statuses):
            raise ValueError("capacity target expectedStatuses must contain valid HTTP statuses")
    slo = raw.get("slo")
    if not isinstance(slo, dict):
        raise ValueError("capacity profile SLO is required")
    if float(slo.get("maxErrorRate", -1)) < 0 or float(slo.get("maxErrorRate", 2)) > 1:
        raise ValueError("maxErrorRate must be between 0 and 1")
    if float(slo.get("p95Ms", 0)) <= 0 or float(slo.get("p99Ms", 0)) <= 0:
        raise ValueError("positive p95Ms and p99Ms SLOs are required")
    timeout = float(raw.get("timeoutSeconds", 10))
    if timeout < 0.1 or timeout > 300:
        raise ValueError("timeoutSeconds must be between 0.1 and 300")
    return raw


async def run_profile(
    profile: dict[str, Any],
    base_url: str,
    headers: dict[str, str] | None = None,
    *,
    transport: Callable[[str, str, dict[str, str], object | None, float], int] | None = None,
) -> dict[str, Any]:
    profile = validate_profile(profile)
    request_count = int(profile["requests"])
    concurrency = int(profile["concurrency"])
    timeout = float(profile.get("timeoutSeconds", 10))
    expanded_targets = [
        target
        for target in profile["targets"]
        for _ in range(int(target["weight"]))
    ]
    next_index = 0
    latencies: list[float] = []
    target_latencies: dict[str, list[float]] = defaultdict(list)
    target_failures: Counter[str] = Counter()
    target_requests: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    executed = 0
    failures = 0
    started = time.perf_counter()
    requester = transport or request_once
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="aegis-capacity") as executor:
        async def worker() -> None:
            nonlocal executed, failures, next_index
            while next_index < request_count:
                index = next_index
                next_index += 1
                target = expanded_targets[index % len(expanded_targets)]
                request_started = time.perf_counter()
                status = 0
                error = ""
                try:
                    status = await loop.run_in_executor(
                        executor,
                        requester,
                        target["method"],
                        base_url + target["path"],
                        headers or {},
                        target.get("json"),
                        timeout,
                    )
                    if status not in {int(item) for item in target["expectedStatuses"]}:
                        error = f"unexpected HTTP {status}"
                except Exception as exc:
                    error = type(exc).__name__
                latency = (time.perf_counter() - request_started) * 1000
                target_name = f"{target['method']} {target['path']}"
                executed += 1
                failures += bool(error)
                statuses[str(status)] += 1
                latencies.append(latency)
                target_latencies[target_name].append(latency)
                target_requests[target_name] += 1
                target_failures[target_name] += bool(error)

        await asyncio.gather(*(worker() for _ in range(concurrency)))

    elapsed = time.perf_counter() - started
    by_target = {}
    for name, observed_latencies in sorted(target_latencies.items()):
        by_target[name] = {
            "requests": target_requests[name],
            "failures": target_failures[name],
            "p95Ms": round(percentile(observed_latencies, 0.95), 2),
            "p99Ms": round(percentile(observed_latencies, 0.99), 2),
        }
    error_rate = failures / max(1, executed)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)
    slo = profile["slo"]
    passed = (
        executed == request_count
        and error_rate <= float(slo["maxErrorRate"])
        and p95 <= float(slo["p95Ms"])
        and p99 <= float(slo["p99Ms"])
    )
    return {
        "schema": "aegis.capacity-receipt/1.0",
        "profile": profile["name"],
        "profileSha256": hashlib.sha256(canonical_json(profile).encode("utf-8")).hexdigest(),
        "buildRevision": os.getenv("AEGIS_COMMIT", "unknown"),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseOrigin": f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}",
        "headerNames": sorted((headers or {}).keys()),
        "workload": {"requests": request_count, "concurrency": concurrency},
        "result": {
            "passed": passed,
            "elapsedSeconds": round(elapsed, 3),
            "requestsPerSecond": round(request_count / max(elapsed, 0.001), 2),
            "failures": failures,
            "errorRate": round(error_rate, 6),
            "p95Ms": round(p95, 2),
            "p99Ms": round(p99, 2),
            "statuses": dict(sorted(statuses.items())),
            "byTarget": by_target,
        },
    }


def parse_headers(values: list[str]) -> dict[str, str]:
    headers = {}
    for value in values:
        name, separator, content = value.partition(":")
        if not separator or not name.strip() or not content.strip():
            raise ValueError("headers must use Name: Value syntax")
        headers[name.strip()] = content.strip()
    return headers


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded AEGIS capacity profile")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--header", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--allow-mutations", action="store_true")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        parser.error("--base-url must be an HTTP(S) origin without credentials, path, query, or fragment")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
        parser.error("remote load requires explicit --allow-remote")
    profile = validate_profile(json.loads(args.profile.read_text(encoding="utf-8")))
    if any(target["method"] not in {"GET", "HEAD"} for target in profile["targets"]) and not args.allow_mutations:
        parser.error("mutating load requires explicit --allow-mutations")
    receipt = asyncio.run(run_profile(profile, args.base_url.rstrip("/"), parse_headers(args.header)))
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if receipt["result"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
