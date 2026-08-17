"""Evidence integrity.

The E component of S_W is worth 0.15 and is computed by re-verifying the chain,
so these tests are the difference between "we have a log" and "we have evidence".
"""
from __future__ import annotations

import json

import pytest

from aegis_white.errors import IntegrityError
from aegis_white.ledger import GENESIS_PREV, Ledger


def test_empty_ledger_verifies(tmp_path):
    assert Ledger(tmp_path / "l.jsonl").verify() == 0


def test_chain_links_to_genesis_then_forward(tmp_path):
    ledger = Ledger(tmp_path / "l.jsonl")
    first = ledger.append({"event": "one"})
    second = ledger.append({"event": "two"})
    assert first.prev_hash == GENESIS_PREV
    assert second.prev_hash == first.record_hash
    assert ledger.verify() == 2


def test_edited_payload_is_detected(tmp_path):
    path = tmp_path / "l.jsonl"
    ledger = Ledger(path)
    ledger.append({"event": "one", "detail": "original"})
    ledger.append({"event": "two"})

    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["payload"]["detail"] = "tampered"
    lines[0] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(IntegrityError, match="hash mismatch at record 0"):
        ledger.verify()


def test_reordering_records_is_detected(tmp_path):
    # Sequence is inside the hash precisely so that moving records is not a way to
    # rewrite history without editing any single record.
    path = tmp_path / "l.jsonl"
    ledger = Ledger(path)
    ledger.append({"event": "one"})
    ledger.append({"event": "two"})
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[1], lines[0]]) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        ledger.verify()


def test_deleting_a_middle_record_is_detected(tmp_path):
    path = tmp_path / "l.jsonl"
    ledger = Ledger(path)
    for i in range(3):
        ledger.append({"event": f"e{i}"})
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        ledger.verify()


def test_appending_a_forged_record_is_detected(tmp_path):
    # An attacker who appends a plausible-looking record without the real chain hash.
    path = tmp_path / "l.jsonl"
    ledger = Ledger(path)
    ledger.append({"event": "one"})
    forged = {
        "sequence": 1,
        "prev_hash": "0" * 64,
        "record_hash": "f" * 64,
        "payload": {"event": "forged"},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(forged, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(IntegrityError):
        ledger.verify()


def test_truncated_line_is_reported_not_silently_skipped(tmp_path):
    path = tmp_path / "l.jsonl"
    ledger = Ledger(path)
    ledger.append({"event": "one"})
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"sequence": 1, "prev_hash":\n')
    with pytest.raises(IntegrityError):
        ledger.verify()


def test_missing_field_is_reported(tmp_path):
    path = tmp_path / "l.jsonl"
    path.write_text(json.dumps({"sequence": 0, "payload": {}}) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="missing field"):
        Ledger(path).verify()
