from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .authorization import EVIDENCE_KEY, sign_bytes, verify_bytes

GENESIS_HASH = "0" * 64


class AuditLedger:
    """Append-only, hash-chained JSONL audit log."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: str, data: dict[str, Any]) -> str:
        with self._lock, _exclusive_file_lock(self.path.with_suffix(self.path.suffix + ".lock")):
            valid, _, error = self.verify()
            if not valid:
                raise ValueError(f"refusing to append to corrupt audit ledger: {error}")
            previous = self._last_hash()
            payload = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                "data": data,
                "previous_sha256": previous,
            }
            digest = _digest(payload)
            record = {**payload, "sha256": digest}
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return digest

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return GENESIS_HASH
        last = ""
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        try:
            return str(json.loads(last)["sha256"])
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError("audit ledger tail is corrupt") from exc

    def verify(self) -> tuple[bool, int, str | None]:
        previous = GENESIS_HASH
        count = 0
        if not self.path.exists():
            return True, 0, None
        with self.path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    claimed = record.pop("sha256")
                except (json.JSONDecodeError, KeyError):
                    return False, count, f"invalid record at line {number}"
                if record.get("previous_sha256") != previous:
                    return False, count, f"broken chain at line {number}"
                actual = _digest(record)
                if claimed != actual:
                    return False, count, f"hash mismatch at line {number}"
                previous = claimed
                count += 1
        return True, count, None


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seal_ledger(ledger_path: Path, seal_path: Path, private_key: Path, password: bytes) -> None:
    valid, count, error = AuditLedger(ledger_path).verify()
    if not valid:
        raise ValueError(f"refusing to seal corrupt audit ledger: {error}")
    digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    payload = {
        "algorithm": "Ed25519",
        "domain": "aegis.evidence-seal.v1",
        "key_purpose": EVIDENCE_KEY,
        "ledger_sha256": digest,
        "records": count,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = base64.b64encode(sign_bytes(canonical, private_key, password, EVIDENCE_KEY)).decode("ascii")
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    with seal_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({**payload, "signature": signature}, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def verify_ledger_seal(ledger_path: Path, seal_path: Path, public_key: Path) -> None:
    if seal_path.stat().st_size > 10_000:
        raise ValueError("ledger seal exceeds the 10 KB safety limit")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    if seal.get("ledger_sha256") != digest:
        raise ValueError("ledger does not match its signed seal")
    payload = {
        "algorithm": seal.get("algorithm"),
        "domain": seal.get("domain"),
        "key_purpose": seal.get("key_purpose"),
        "ledger_sha256": seal.get("ledger_sha256"),
        "records": seal.get("records"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        signature = base64.b64decode(seal["signature"], validate=True)
    except (KeyError, ValueError) as exc:
        raise ValueError("ledger seal signature is malformed") from exc
    verify_bytes(canonical, signature, public_key, EVIDENCE_KEY)


@contextmanager
def _exclusive_file_lock(path: Path):
    """Cross-process lock with a five-second fail-closed timeout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + 5.0
    locked = False
    try:
        while not locked:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("timed out acquiring audit ledger lock")
                time.sleep(0.05)
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
