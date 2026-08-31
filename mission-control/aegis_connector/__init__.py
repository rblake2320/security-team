"""AEGIS customer-edge connector.

The connector is the execution boundary between Mission Control and assets that
remain in a customer-owned environment.  It accepts only leased, capability-
scoped work and independently enforces local path and hostname allowlists.
"""

from .config import ConnectorConfig
from .worker import ConnectorWorker

__all__ = ["ConnectorConfig", "ConnectorWorker"]
__version__ = "1.0.0"
