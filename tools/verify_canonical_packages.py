from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "00-shared" / "config" / "canonical_implementations.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["package_identities"]
    discovered: dict[str, list[Path]] = {}
    for pyproject in ROOT.rglob("pyproject.toml"):
        if any(part in {".git", ".venv", "build", "dist"} for part in pyproject.parts):
            continue
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        name = data.get("project", {}).get("name")
        if isinstance(name, str):
            discovered.setdefault(name, []).append(pyproject.parent.resolve())

    errors: list[str] = []
    for identity, record in expected.items():
        canonical = (ROOT / record["canonical_path"]).resolve()
        locations = discovered.get(identity, [])
        if locations != [canonical]:
            shown = ", ".join(str(path.relative_to(ROOT)) for path in locations) or "none"
            errors.append(f"{identity}: expected only {record['canonical_path']}; found {shown}")
        for archive in record.get("archive_paths", []):
            if (ROOT / archive / "pyproject.toml").exists():
                errors.append(f"{identity}: archived path remains buildable: {archive}")

    unmanaged = sorted(set(discovered) - set(expected))
    if unmanaged:
        errors.append("unregistered package identities: " + ", ".join(unmanaged))
    if errors:
        print("CANONICAL PACKAGE CHECK: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"CANONICAL PACKAGE CHECK: PASS ({len(expected)} unique identities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
