from __future__ import annotations

import re
import socket
import struct
from dataclasses import dataclass


class ScannerUnavailable(RuntimeError):
    """Raised when the configured evidence scanner cannot return a trusted verdict."""


@dataclass(frozen=True)
class ScanResult:
    status: str
    engine: str
    signature: str | None = None


class DisabledEvidenceScanner:
    mode = "disabled"
    enabled = False

    def ping(self) -> bool:
        return True

    def scan_bytes(self, content: bytes) -> ScanResult:
        del content
        raise ScannerUnavailable("evidence scanner is disabled")


class ClamAVScanner:
    """Small fail-closed client for clamd's private-network-only INSTREAM API."""

    mode = "clamav"
    enabled = True
    _MAX_RESPONSE_BYTES = 4096
    _CHUNK_BYTES = 64 * 1024

    def __init__(self, host: str, port: int = 3310, timeout_seconds: int = 30):
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds

    def _connect(self) -> socket.socket:
        try:
            connection = socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout_seconds,
            )
            connection.settimeout(self.timeout_seconds)
            return connection
        except OSError as exc:
            raise ScannerUnavailable("malware scanner is unavailable") from exc

    @classmethod
    def _read_response(cls, connection: socket.socket) -> str:
        payload = bytearray()
        try:
            while len(payload) < cls._MAX_RESPONSE_BYTES:
                chunk = connection.recv(min(1024, cls._MAX_RESPONSE_BYTES - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if b"\0" in chunk or b"\n" in chunk:
                    break
        except OSError as exc:
            raise ScannerUnavailable("malware scanner did not return a verdict") from exc
        if not payload or len(payload) >= cls._MAX_RESPONSE_BYTES:
            raise ScannerUnavailable("malware scanner returned an invalid verdict")
        return bytes(payload).split(b"\0", 1)[0].decode("utf-8", "replace").strip()

    def ping(self) -> bool:
        try:
            with self._connect() as connection:
                connection.sendall(b"zPING\0")
                return self._read_response(connection) == "PONG"
        except ScannerUnavailable:
            return False

    def scan_bytes(self, content: bytes) -> ScanResult:
        if not content:
            raise ValueError("scanner requires non-empty evidence")
        try:
            with self._connect() as connection:
                connection.sendall(b"zINSTREAM\0")
                view = memoryview(content)
                for offset in range(0, len(view), self._CHUNK_BYTES):
                    chunk = view[offset : offset + self._CHUNK_BYTES]
                    connection.sendall(struct.pack("!I", len(chunk)))
                    connection.sendall(chunk)
                connection.sendall(struct.pack("!I", 0))
                response = self._read_response(connection)
        except ScannerUnavailable:
            raise
        except OSError as exc:
            raise ScannerUnavailable("malware scanner stream failed") from exc

        if response == "stream: OK":
            return ScanResult(status="clean", engine="clamav")
        match = re.fullmatch(r"stream: (.{1,240}) FOUND", response)
        if match:
            signature = re.sub(r"[^A-Za-z0-9._:+ -]", "?", match.group(1))[:160]
            return ScanResult(status="rejected", engine="clamav", signature=signature)
        raise ScannerUnavailable("malware scanner did not return a recognized verdict")


def build_evidence_scanner(
    mode: str,
    *,
    host: str,
    port: int,
    timeout_seconds: int,
) -> DisabledEvidenceScanner | ClamAVScanner:
    if mode == "disabled":
        return DisabledEvidenceScanner()
    if mode == "clamav":
        return ClamAVScanner(host, port, timeout_seconds)
    raise ValueError("unknown evidence scanner mode")
