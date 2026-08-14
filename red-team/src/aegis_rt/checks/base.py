from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..models import CheckResult, Limits, Target, TargetKind


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class ExecutionContext:
    limits: Limits
    kill_switch: Path
    allow_public_targets: bool = False
    _requests: int = 0
    _files: int = 0
    _last_request: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def assert_running(self) -> None:
        if self.kill_switch.exists():
            raise InterruptedError(f"kill switch activated: {self.kill_switch}")

    def consume_request(self) -> None:
        with self._lock:
            self.assert_running()
            if self._requests >= self.limits.max_requests:
                raise BudgetExceeded("engagement request budget exhausted")
            delay = (1.0 / self.limits.requests_per_second) - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            self._requests += 1
            self._last_request = time.monotonic()

    def consume_file(self) -> None:
        with self._lock:
            self.assert_running()
            if self._files >= self.limits.max_files:
                raise BudgetExceeded("engagement file budget exhausted")
            self._files += 1

    @property
    def requests_used(self) -> int:
        with self._lock:
            return self._requests

    @property
    def files_used(self) -> int:
        with self._lock:
            return self._files


class Check(Protocol):
    check_id: str
    target_kinds: frozenset[TargetKind]
    description: str
    active: bool

    def run(self, target: Target, context: ExecutionContext) -> CheckResult: ...
