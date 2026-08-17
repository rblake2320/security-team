class YellowError(ValueError):
    """Base error for rejected Yellow Team operations."""


class ConfigurationError(YellowError):
    """A configuration or frozen artifact is invalid."""


class RemediationError(YellowError):
    """A finding cannot be closed in the way requested.

    Distinct from ConfigurationError because closing a finding without evidence is
    the specific failure this team exists to prevent: the charter requires findings
    to become "completed engineering work with verifiable acceptance criteria".
    """


class IntegrityError(YellowError):
    """Stored evidence or audit state failed integrity validation."""
