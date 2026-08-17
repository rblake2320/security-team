"""Append-only, hash-chained evidence ledger.

Every White Team decision is evidence. A governance record that can be edited after
the fact is worth nothing in an after-action review, so each record commits to the
hash of the record before it. Changing any byte of any earlier record breaks the
chain at that point and `verify` reports the first bad line.

The chain is the mechanism behind the scorecard's E (evidence integrity) component:
E is not self-asserted, it is computed by re-verifying this file.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .canonical import canonical_bytes, load_json_bounded
from .errors import IntegrityError

GENESIS_PREV = "0" * 64


def _record_hash(prev_hash: str, payload: Any, sequence: int) -> str:
    """Hash over (previous hash, sequence, payload).

    The sequence number is inside the hash so that reordering records — not just
    editing them — also breaks the chain.
    """
    material = canonical_bytes({"prev": prev_hash, "seq": sequence, "payload": payload})
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class LedgerRecord:
    sequence: int
    prev_hash: str
    record_hash: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {
                "sequence": self.sequence,
                "prev_hash": self.prev_hash,
                "record_hash": self.record_hash,
                "payload": self.payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


class Ledger:
    """A hash-chained JSONL ledger.

    Append is durable: the line is flushed and fsynced before the call returns, so a
    process killed mid-run leaves a verifiable prefix rather than a truncated record.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    # ---- reading -------------------------------------------------------------

    def __iter__(self) -> Iterator[LedgerRecord]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = load_json_bounded(line.encode("utf-8"))
                except Exception as exc:  # noqa: BLE001 - reported with position
                    raise IntegrityError(f"unreadable ledger line {line_number}: {exc}") from exc
                if not isinstance(raw, dict):
                    raise IntegrityError(f"ledger line {line_number} is not an object")
                missing = {"sequence", "prev_hash", "record_hash", "payload"} - set(raw)
                if missing:
                    raise IntegrityError(
                        f"ledger line {line_number} missing field(s): {', '.join(sorted(missing))}"
                    )
                yield LedgerRecord(
                    sequence=raw["sequence"],
                    prev_hash=raw["prev_hash"],
                    record_hash=raw["record_hash"],
                    payload=raw["payload"],
                )

    def head(self) -> tuple[int, str]:
        """Return (last sequence, last hash) without validating the whole chain."""
        sequence, digest = -1, GENESIS_PREV
        for record in self:
            sequence, digest = record.sequence, record.record_hash
        return sequence, digest

    # ---- writing -------------------------------------------------------------

    def append(self, payload: dict[str, Any]) -> LedgerRecord:
        sequence, prev_hash = self.head()
        record = LedgerRecord(
            sequence=sequence + 1,
            prev_hash=prev_hash,
            record_hash=_record_hash(prev_hash, payload, sequence + 1),
            payload=payload,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    # ---- verification --------------------------------------------------------

    def verify(self) -> int:
        """Re-derive the whole chain. Returns the record count, or raises IntegrityError.

        Deliberately recomputes every hash rather than trusting the stored value:
        trusting `record_hash` as written would make the chain self-certifying and
        therefore useless.
        """
        expected_prev = GENESIS_PREV
        count = 0
        for index, record in enumerate(self):
            if record.sequence != index:
                raise IntegrityError(
                    f"sequence gap at record {index}: found {record.sequence}"
                )
            if record.prev_hash != expected_prev:
                raise IntegrityError(f"broken chain at record {index}: prev_hash mismatch")
            recomputed = _record_hash(record.prev_hash, record.payload, record.sequence)
            if recomputed != record.record_hash:
                raise IntegrityError(f"hash mismatch at record {index}")
            expected_prev = record.record_hash
            count += 1
        return count
