class PurpleError(ValueError):
    """Base error for rejected Purple Team operations."""


class ConfigurationError(PurpleError):
    """A configuration or frozen artifact is invalid."""


class TransitionError(PurpleError):
    """An exercise lifecycle transition is not authorized."""


class IntegrityError(PurpleError):
    """Stored evidence or audit state failed integrity validation."""

