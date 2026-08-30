from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ALLOWED_CONTENT_TYPES = {
    "application/gzip",
    "application/json",
    "application/msword",
    "application/pdf",
    "application/rtf",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-7z-compressed",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/xml",
    "application/zip",
    "application/octet-stream",
    "audio/flac",
    "audio/m4a",
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
    "text/csv",
    "text/css",
    "text/html",
    "text/javascript",
    "text/markdown",
    "text/plain",
    "text/xml",
    "text/yaml",
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
}


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    sha256: str
    size_bytes: int
    filename: str
    content_type: str


class EvidenceStore:
    MAGIC = b"AEGIS1"

    def __init__(self, root: Path, max_bytes: int, master_key: str = "development-evidence-key-not-production"):
        self.root = root.resolve()
        self.max_bytes = max_bytes
        if master_key == "development-evidence-key-not-production":
            self.master_key = hashlib.sha256(master_key.encode("utf-8")).digest()
        else:
            import base64

            padded = master_key + "=" * (-len(master_key) % 4)
            self.master_key = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(self.master_key) != 32:
            raise ValueError("evidence master key must decode to exactly 32 bytes")
        self.root.mkdir(parents=True, exist_ok=True)

    def tenant_key(self, organization_id: str) -> bytes:
        return hmac.new(self.master_key, f"evidence:{organization_id}".encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def safe_filename(value: str) -> str:
        name = Path(value.replace("\x00", "")).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
        return (name or "evidence.bin")[:180]

    def put(self, organization_id: str, filename: str, content_type: str, content: bytes) -> StoredObject:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("content type is not permitted")
        if not content or len(content) > self.max_bytes:
            raise ValueError(f"evidence must be between 1 and {self.max_bytes} bytes")
        digest = hashlib.sha256(content).hexdigest()
        safe_name = self.safe_filename(filename)
        storage_key = f"{organization_id}/{digest[:2]}/{uuid.uuid4().hex}.aegis"
        destination = (self.root / storage_key).resolve()
        try:
            destination.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("invalid evidence path") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".partial")
        nonce = os.urandom(12)
        encrypted = AESGCM(self.tenant_key(organization_id)).encrypt(
            nonce,
            content,
            organization_id.encode("utf-8"),
        )
        with temporary.open("xb") as handle:
            handle.write(self.MAGIC + nonce + encrypted)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
        return StoredObject(storage_key, digest, len(content), safe_name, content_type)

    def get(self, organization_id: str, storage_key: str) -> bytes:
        if not storage_key.startswith(f"{organization_id}/"):
            raise PermissionError("evidence object belongs to a different workspace")
        target = (self.root / storage_key).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("invalid evidence path") from exc
        payload = target.read_bytes()
        if len(payload) < len(self.MAGIC) + 12 + 16 or not payload.startswith(self.MAGIC):
            raise ValueError("evidence object is not a valid encrypted envelope")
        nonce = payload[len(self.MAGIC):len(self.MAGIC) + 12]
        ciphertext = payload[len(self.MAGIC) + 12:]
        return AESGCM(self.tenant_key(organization_id)).decrypt(
            nonce,
            ciphertext,
            organization_id.encode("utf-8"),
        )

    def delete(self, storage_key: str) -> bool:
        target = (self.root / storage_key).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return False
        if not target.is_file():
            return False
        target.unlink()
        return True
