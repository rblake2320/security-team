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

    def test_production_release_is_gated_on_real_evidence_scanner(self) -> None:
        compose = (MISSION_ROOT / "deploy" / "vps" / "compose.production.yml").read_text(encoding="utf-8")
        release = (MISSION_ROOT / "deploy" / "vps" / "release.sh").read_text(encoding="utf-8")
        production_env = (MISSION_ROOT / "deploy" / "vps" / ".env.production.example").read_text(encoding="utf-8")
        workflow = (MISSION_ROOT.parent / ".github" / "workflows" / "mission-control.yml").read_text(encoding="utf-8")
        self.assertRegex(compose, r"image: clamav/clamav:[^\s]+@sha256:[0-9a-f]{64}")
        self.assertIn("clamav-signatures:/var/lib/clamav", compose)
        self.assertIn("condition: service_healthy", compose)
        clamav_section = compose.split("\n  clamav:", 1)[1].split("\n  app:", 1)[0]
        self.assertNotIn("\n    ports:", clamav_section)
        self.assertIn("up --detach clamav", release)
        self.assertIn("wait_healthy compose.production.yml .env.production clamav 210", release)
        self.assertIn("EVIDENCE_SCANNER_MODE=clamav", production_env)
        self.assertIn("--entrypoint python", workflow)
        self.assertIn("mission-control/tools/verify_clamav.py:/tmp/verify_clamav.py:ro", workflow)
        self.assertIn("--env PYTHONPATH=/app", workflow)
        self.assertLess(
            workflow.index("- name: Build production image"),
            workflow.index("- name: Verify real ClamAV evidence scanning"),
        )
        self.assertRegex(workflow, r"clamav/clamav:[^\s]+@sha256:[0-9a-f]{64}")

    def test_production_uses_restricted_database_role_and_real_rls_gate(self) -> None:
        production_env = (MISSION_ROOT / "deploy" / "vps" / ".env.production.example").read_text(
            encoding="utf-8"
        )
        entrypoint = (MISSION_ROOT / "deploy" / "vps" / "entrypoint.sh").read_text(encoding="utf-8")
        release = (MISSION_ROOT / "deploy" / "vps" / "release.sh").read_text(encoding="utf-8")
        workflow = (MISSION_ROOT.parent / ".github" / "workflows" / "mission-control.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("DATABASE_ADMIN_URL=", production_env)
        self.assertIn("AEGIS_DB_RUNTIME_PASSWORD=", production_env)
        self.assertNotIn("\nDATABASE_URL=", "\n" + production_env)
        self.assertIn('DATABASE_URL="$DATABASE_ADMIN_URL" alembic upgrade head', entrypoint)
        self.assertIn("python -m aegis_platform.db_roles provision", entrypoint)
        self.assertIn("python -m aegis_platform.db_roles runtime-url", entrypoint)
        self.assertIn("database did not reach the reviewed migration head", release)
        self.assertIn("MIGRATION_BEFORE=", release)
        self.assertIn("Verify PostgreSQL row-level tenant isolation", workflow)
        self.assertIn("verify_postgres_rls.py:/tmp/verify_postgres_rls.py:ro", workflow)
        self.assertRegex(workflow, r"postgres:16-alpine@sha256:[0-9a-f]{64}")


if __name__ == "__main__":
    unittest.main()
