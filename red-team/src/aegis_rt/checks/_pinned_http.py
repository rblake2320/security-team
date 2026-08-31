"""Shared address-pinned HTTP(S) connection classes.

Extracted from http_headers.py so DNS-rebinding-safe connection logic exists in exactly
one place - any active HTTP check needs this same pinning, and duplicating
security-sensitive networking code across checks is worse than one shared import.
"""

from __future__ import annotations

import http.client
import socket
import ssl


class PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout, self.source_address)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int, timeout: float):
        super().__init__(hostname, port, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self) -> None:
        raw = socket.create_connection((self._address, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def connection_for(scheme: str, hostname: str, address: str, port: int, timeout: float):
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported HTTP scheme: {scheme}")
    connection_type = PinnedHTTPSConnection if scheme == "https" else PinnedHTTPConnection
    return connection_type(hostname, address, port, timeout)
