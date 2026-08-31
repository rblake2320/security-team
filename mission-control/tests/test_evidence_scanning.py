from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis_platform.api import create_app
from aegis_platform.config import Settings
from aegis_platform.scanner import ClamAVScanner, ScanResult, ScannerUnavailable


class MutableScanner(ClamAVScanner):
    def __init__(self) -> None:
        self.available = True
        self.result = ScanResult(status="clean", engine="clamav")

    def ping(self) -> bool:
        return self.available

    def scan_bytes(self, content: bytes) -> ScanResult:
        assert content
        if not self.available:
            raise ScannerUnavailable("synthetic scanner outage")
        return self.result


def scanner_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite:///{(tmp_path / 'platform.db').as_posix()}",
        evidence_root=tmp_path / "evidence",
        auth_mode="development",
        token_pepper=("test-pepper-" * 4)[:32],
        bootstrap_email="owner@example.test",
        bootstrap_organization="Owner Workspace",
        bootstrap_slug="owner",
        max_evidence_bytes=1024 * 1024,
        lease_seconds=60,
        evidence_scanner_mode="clamav",
        clamav_host="clamav",
    )


def test_engine_verdict_controls_evidence_and_outages_fail_closed(tmp_path: Path) -> None:
    scanner = MutableScanner()
    app = create_app(scanner_settings(tmp_path), evidence_scanner=scanner)
    with TestClient(app) as client:
        clean_upload = client.post(
            "/api/v1/evidence",
            files={"file": ("clean.txt", b"bounded clean evidence", "text/plain")},
        )
        assert clean_upload.status_code == 201
        clean_id = clean_upload.json()["evidence"]["id"]
        assert clean_upload.json()["evidence"]["scanStatus"] == "clean"
        assert client.get(f"/api/v1/evidence/{clean_id}/download").status_code == 200

        scanner.result = ScanResult(
            status="rejected",
            engine="clamav",
            signature="Win.Test.EICAR_HDB-1",
        )
        override = client.post(
            f"/api/v1/evidence/{clean_id}/scan",
            json={"status": "clean", "note": "Attempted manual clean override."},
        )
        assert override.status_code == 200
        assert override.json() == {
            "id": clean_id,
            "scanStatus": "rejected",
            "scanner": "clamav",
        }
        assert client.get(f"/api/v1/evidence/{clean_id}/download").status_code == 403

        rejected_upload = client.post(
            "/api/v1/evidence",
            files={"file": ("eicar.txt", b"synthetic rejected evidence", "text/plain")},
        )
        assert rejected_upload.status_code == 201
        assert rejected_upload.json()["evidence"]["scanStatus"] == "rejected"

        scanner.available = False
        quarantined_upload = client.post(
            "/api/v1/evidence",
            files={"file": ("unscanned.txt", b"scanner outage evidence", "text/plain")},
        )
        assert quarantined_upload.status_code == 201
        quarantined_id = quarantined_upload.json()["evidence"]["id"]
        assert quarantined_upload.json()["evidence"]["scanStatus"] == "quarantined"
        assert client.get(f"/api/v1/evidence/{quarantined_id}/download").status_code == 403
        assert client.get("/api/ready").status_code == 503
        failed_override = client.post(
            f"/api/v1/evidence/{quarantined_id}/scan",
            json={"status": "clean", "note": "Scanner is unavailable."},
        )
        assert failed_override.status_code == 503
        listed = client.get("/api/v1/evidence").json()["evidence"]
        assert next(row for row in listed if row["id"] == quarantined_id)["scanStatus"] == "quarantined"


def test_production_configuration_requires_real_scanner() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://aegis:password@db:5432/aegis",
        evidence_root=Path("/var/lib/aegis/evidence"),
        evidence_master_key=base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("="),
        auth_mode="cloudflare",
        cloudflare_team_domain="team.cloudflareaccess.com",
        cloudflare_audience="audience",
        public_hostname="mission.aegis.example",
        token_pepper=("test-pepper-" * 4)[:32],
        bootstrap_email="owner@aegis.example",
        evidence_scanner_mode="disabled",
    )
    with pytest.raises(RuntimeError, match="EVIDENCE_SCANNER_MODE must be clamav in production"):
        settings.validate()
