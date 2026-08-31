#!/usr/bin/env python3
"""Fail-closed structural validator for the application-security baseline."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "00-shared" / "config" / "application_security_baseline.json"

TOP_LEVEL_KEYS = {"schema", "version", "document", "control_owners", "controls"}
CONTROL_KEYS = {"id", "source", "title", "risk", "invariant", "negative_tests"}
OWNER_KEYS = {
    "abuse_case",
    "implementation_and_regression",
    "telemetry",
    "controlled_exercise",
    "independent_authorized_assessment",
}
SOURCES = {"source-notes", "owasp-api-2023"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(document: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if set(document) != TOP_LEVEL_KEYS:
        errors.append(f"top-level keys must be exactly {sorted(TOP_LEVEL_KEYS)}")
    if document.get("schema") != "program.application-security-baseline/1.0":
        errors.append("unsupported or missing schema")
    if not _nonempty(document.get("version")):
        errors.append("version must be a non-empty string")

    owners = document.get("control_owners")
    if not isinstance(owners, dict) or set(owners) != OWNER_KEYS:
        errors.append(f"control_owners keys must be exactly {sorted(OWNER_KEYS)}")
    elif any(not _nonempty(value) for value in owners.values()):
        errors.append("every control owner must be a non-empty string")

    controls = document.get("controls")
    if not isinstance(controls, list):
        errors.append("controls must be a list")
        controls = []
    expected_ids = [f"APP-{number:02d}" for number in range(1, 11)]
    actual_ids = [item.get("id") for item in controls if isinstance(item, dict)]
    if actual_ids != expected_ids:
        errors.append(f"controls must appear exactly once in order: {expected_ids}")

    for index, control in enumerate(controls, start=1):
        label = f"control[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{label} must be an object")
            continue
        if set(control) != CONTROL_KEYS:
            errors.append(f"{label} keys must be exactly {sorted(CONTROL_KEYS)}")
        for field in ("id", "title", "risk", "invariant"):
            if not _nonempty(control.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string")
        if control.get("source") not in SOURCES:
            errors.append(f"{label}.source must be one of {sorted(SOURCES)}")
        tests = control.get("negative_tests")
        if not isinstance(tests, list) or len(tests) < 2:
            errors.append(f"{label}.negative_tests must contain at least two tests")
        elif any(not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", item or "") for item in tests):
            errors.append(f"{label}.negative_tests entries must be lower_snake_case")
        elif len(tests) != len(set(tests)):
            errors.append(f"{label}.negative_tests contains duplicates")

    doc_path_value = document.get("document")
    if not _nonempty(doc_path_value):
        errors.append("document must be a repository-relative path")
    else:
        doc_path = (root / doc_path_value).resolve()
        try:
            doc_path.relative_to(root.resolve())
        except ValueError:
            errors.append("document must remain inside the repository")
        else:
            if not doc_path.is_file():
                errors.append(f"document does not exist: {doc_path_value}")
            else:
                text = doc_path.read_text(encoding="utf-8")
                missing_rows = [str(number) for number in range(1, 11)
                                if f"| {number} |" not in text]
                if missing_rows:
                    errors.append("document is missing control table rows: " + ", ".join(missing_rows))
                if "actor -> action -> resource -> allowed fields -> workflow state -> limits" not in text:
                    errors.append("document is missing the server-side authorization invariant")
    return errors


def main() -> int:
    try:
        document = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"application security baseline: FAIL: {exc}")
        return 1
    errors = validate(document)
    if errors:
        for error in errors:
            print(f"  ERROR {error}")
        print(f"application security baseline: FAIL ({len(errors)} error(s))")
        return 1
    print("application security baseline: PASS (10 controls, negative tests, owners, document parity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
