from __future__ import annotations

import re
import unittest
from pathlib import Path


MISSION_ROOT = Path(__file__).resolve().parents[1]


class ProductionReleaseContractTests(unittest.TestCase):
    def test_release_rolls_back_postflight_failures_and_probes_showcase_directly(self) -> None:
        script = (MISSION_ROOT / "deploy" / "vps" / "release.sh").read_text(encoding="utf-8")
        trap_position = script.index("trap on_exit 0")
        switch_position = script.index('mv -Tf /opt/aegis/current.next "$current"')
        self.assertLess(trap_position, switch_position)
        self.assertIn("rollback ||", script)
        self.assertIn("exec -T showcase python -c", script)
        self.assertNotIn("--header 'Host: showcase.aihangout.ai' http://127.0.0.1:8780", script)
        self.assertIn("archive contains an unsafe path", script)
        self.assertIn("archive commit receipt does not match", script)
        self.assertIn('org.opencontainers.image.revision', script)

    def test_runtime_and_infrastructure_base_images_are_digest_pinned(self) -> None:
        dockerfile = (MISSION_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertRegex(dockerfile, r"FROM node:22-alpine@sha256:[0-9a-f]{64}")
        self.assertRegex(dockerfile, r"FROM python:3\.12-slim@sha256:[0-9a-f]{64}")
        self.assertIn('LABEL org.opencontainers.image.revision="$AEGIS_COMMIT"', dockerfile)

        for name in ("compose.production.yml", "compose.showcase.yml"):
            compose = (MISSION_ROOT / "deploy" / "vps" / name).read_text(encoding="utf-8")
            images = re.findall(r"^\s+image:\s+([^\s]+)", compose, re.MULTILINE)
            third_party = [image for image in images if not image.startswith("aegis-mission-control")]
            self.assertTrue(third_party)
            for image in third_party:
                self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
