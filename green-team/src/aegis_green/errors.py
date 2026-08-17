class GreenError(ValueError):
    """Base error for rejected Green Team operations."""


class ConfigurationError(GreenError):
    """A configuration or frozen artifact is invalid."""


class CoverageError(GreenError):
    """A coverage claim is not supported by the recorded telemetry.

    Separate from ConfigurationError because Green's charter is to make systems
    "observable and defensible BEFORE production" — an unsupported coverage claim is
    the specific failure that puts an undefendable system into production.
    """


class IntegrityError(GreenError):
    """Stored evidence or audit state failed integrity validation."""
