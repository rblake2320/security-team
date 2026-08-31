#!/usr/bin/env python3
from __future__ import annotations

import os

from aegis_platform.scanner import ClamAVScanner


def main() -> int:
    scanner = ClamAVScanner(
        os.getenv("CLAMAV_HOST", "127.0.0.1"),
        int(os.getenv("CLAMAV_PORT", "3310")),
        timeout_seconds=30,
    )
    if not scanner.ping():
        raise RuntimeError("ClamAV did not answer PING")
    clean = scanner.scan_bytes(b"AEGIS bounded clean integration evidence")
    if clean.status != "clean":
        raise RuntimeError(f"clean evidence received {clean.status!r}")
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    rejected = scanner.scan_bytes(eicar)
    if rejected.status != "rejected" or not rejected.signature:
        raise RuntimeError("EICAR evidence was not rejected with a signature")
    print("CLAMAV_PING=PASS")
    print("CLAMAV_CLEAN=PASS")
    print("CLAMAV_EICAR_REJECTION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
