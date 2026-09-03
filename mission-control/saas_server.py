#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import uvicorn

from aegis_platform.initialize import initialize_from_env

from aegis_platform.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description="AEGIS standalone Mission Control SaaS")
    parser.add_argument("--host", default=os.getenv("AEGIS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AEGIS_PORT", "8780")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("AEGIS_WORKERS", "1")))
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.environment != "production" and args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Non-production environments must bind to loopback")
    initialize_from_env()
    os.environ["AEGIS_SKIP_INITIALIZATION"] = "1"
    uvicorn.run(
        "aegis_platform.api:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        workers=args.workers,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1" if settings.environment != "production" else "*",
        server_header=False,
        date_header=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
