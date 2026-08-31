from __future__ import annotations

import os
import socketserver
import struct
import threading

import pytest

from aegis_platform.scanner import ClamAVScanner, ScannerUnavailable


def eicar_test_bytes() -> bytes:
    # Split construction avoids accidental host antivirus treatment of this source file.
    return b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class FakeClamdHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        command = bytearray()
        while b"\0" not in command:
            chunk = self.request.recv(64)
            if not chunk:
                return
            command.extend(chunk)
        initial, remainder = bytes(command).split(b"\0", 1)
        if initial == b"zPING":
            self.request.sendall(b"PONG\0")
            return
        if initial != b"zINSTREAM":
            self.request.sendall(b"UNKNOWN COMMAND ERROR\0")
            return

        payload = bytearray()
        buffered = bytearray(remainder)

        def read_exact(size: int) -> bytes:
            while len(buffered) < size:
                part = self.request.recv(max(4096, size - len(buffered)))
                if not part:
                    raise ConnectionError("incomplete fake clamd stream")
                buffered.extend(part)
            result = bytes(buffered[:size])
            del buffered[:size]
            return result

        while True:
            size = struct.unpack("!I", read_exact(4))[0]
            if size == 0:
                break
            payload.extend(read_exact(size))
        if bytes(payload) == b"malformed-verdict":
            self.request.sendall(b"stream: unexpected\0")
        elif b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in payload:
            self.request.sendall(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")
        else:
            self.request.sendall(b"stream: OK\0")


class FakeClamdServer:
    def __enter__(self) -> tuple[str, int]:
        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeClamdHandler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        return str(host), int(port)

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_clamav_protocol_clean_infected_and_unrecognized_verdicts() -> None:
    with FakeClamdServer() as (host, port):
        scanner = ClamAVScanner(host, port, timeout_seconds=2)
        assert scanner.ping() is True
        assert scanner.scan_bytes(b"bounded evidence").status == "clean"
        rejected = scanner.scan_bytes(eicar_test_bytes())
        assert rejected.status == "rejected"
        assert rejected.signature == "Win.Test.EICAR_HDB-1"
        with pytest.raises(ScannerUnavailable):
            scanner.scan_bytes(b"malformed-verdict")


@pytest.mark.skipif(
    os.getenv("AEGIS_CLAMAV_INTEGRATION") != "1",
    reason="requires the explicitly provisioned ClamAV integration service",
)
def test_real_clamav_detects_eicar_and_accepts_clean_bytes() -> None:
    scanner = ClamAVScanner(
        os.getenv("CLAMAV_HOST", "127.0.0.1"),
        int(os.getenv("CLAMAV_PORT", "3310")),
        timeout_seconds=30,
    )
    assert scanner.ping() is True
    assert scanner.scan_bytes(b"AEGIS bounded clean integration evidence").status == "clean"
    rejected = scanner.scan_bytes(eicar_test_bytes())
    assert rejected.status == "rejected"
    assert rejected.signature
