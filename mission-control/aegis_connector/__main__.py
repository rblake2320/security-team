from __future__ import annotations

import argparse
import json

from .client import ConnectorAPI
from .config import ConnectorConfig
from .worker import ConnectorWorker


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AEGIS customer-edge execution connector")
    parser.add_argument("--once", action="store_true", help="heartbeat, process at most one task, and exit")
    parser.add_argument("--doctor", action="store_true", help="validate configuration and prove the control-plane connection")
    args = parser.parse_args()
    config = ConnectorConfig.from_env()
    worker = ConnectorWorker(config)
    if args.doctor:
        response = ConnectorAPI(config).heartbeat(worker.agents())
        print(json.dumps({"ok": bool(response.get("accepted")), **config.public_summary()}, indent=2))
        return 0
    if args.once:
        worker.run_once()
        return 0
    worker.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
