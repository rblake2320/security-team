class WhiteError(ValueError):
    """Base error for rejected White Team operations."""


class ConfigurationError(WhiteError):
    """A configuration or frozen artifact is invalid."""


class AuthorizationError(WhiteError):
    """An action is outside the authorized scope, or authorization is absent/expired."""


class StopViolationError(WhiteError):
    """Activity was attempted after a mandatory stop condition was declared.

    This is the White Team's one unconditional control. It is a distinct error type
    because the scorecard treats it as an automatic failure rather than a deduction.
    """


class IntegrityError(WhiteError):
    """Stored evidence or audit state failed integrity validation."""
