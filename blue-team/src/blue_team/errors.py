"""Typed, operator-safe errors."""


class BlueTeamError(Exception):
    """Base error for expected operational failures."""


class ValidationError(BlueTeamError):
    """Input failed strict validation."""


class IntegrityError(BlueTeamError):
    """Stored evidence failed integrity validation."""


class ConfigurationError(BlueTeamError):
    """Rule or policy configuration is unsafe or malformed."""
