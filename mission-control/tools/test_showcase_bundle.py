#!/usr/bin/env python3
"""Fail when the public showcase ships operator routes or source maps."""

from __future__ import annotations

import re
from pathlib import Path


MISSION_ROOT = Path(__file__).resolve().parents[1]
DIST = MISSION_ROOT / "web" / "dist"
DEPLOY_ROOT = MISSION_ROOT / "deploy" / "vps"


def main() -> int:
    assert (DIST / "index.html").is_file(), "showcase build is missing web/dist/index.html"
    profile = DIST / "aegis-build-profile.txt"
    assert profile.is_file() and profile.read_text(encoding="utf-8").strip() == "showcase", (
        "showcase build profile receipt is missing or incorrect"
    )
    scripts = sorted((DIST / "assets").glob("*.js"))
    maps = sorted(DIST.rglob("*.map"))
    assert scripts, "showcase build contains no JavaScript bundle"
    assert not maps, f"showcase build contains public source maps: {maps}"

    bundle = "\n".join(script.read_text(encoding="utf-8") for script in scripts)
    assert "sourceMappingURL" not in bundle, "showcase bundle advertises a source map"
    assert "/api/snapshot" in bundle, "showcase bundle lost its read-only snapshot feed"
    for forbidden in ("/api/runs", "/api/v1/"):
        assert forbidden not in bundle, f"showcase bundle exposes private operator route family {forbidden}"

    production_compose = (DEPLOY_ROOT / "compose.production.yml").read_text(encoding="utf-8")
    showcase_compose = (DEPLOY_ROOT / "compose.showcase.yml").read_text(encoding="utf-8")
    image_pattern = r"^\s+image:\s*(aegis-mission-control[^\s]*)"
    production_image = re.search(image_pattern, production_compose, re.MULTILINE)
    showcase_image = re.search(image_pattern, showcase_compose, re.MULTILINE)
    assert production_image and showcase_image, "deployment image names are missing"
    assert production_image.group(1) != showcase_image.group(1), (
        "operator and showcase Compose stacks must not reuse an image tag"
    )

    print("SHOWCASE_SOURCE_MAPS=PASS")
    print("SHOWCASE_PRIVATE_ROUTES=PASS")
    print("SHOWCASE_SNAPSHOT_ONLY=PASS")
    print("SHOWCASE_IMAGE_ISOLATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
