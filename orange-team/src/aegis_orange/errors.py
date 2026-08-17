class OrangeError(ValueError):
    """Base error for rejected Orange Team operations."""


class ConfigurationError(OrangeError):
    """A configuration or frozen artifact is invalid."""


class UnsafeTestError(OrangeError):
    """A proposed test is not safe to run at design/build time.

    Orange works pre-production alongside builders. "Any unsafe testing performed"
    is an automatic scorecard failure, so unsafe proposals are refused at the point
    of definition rather than caught afterwards.
    """


class IntegrityError(OrangeError):
    """Stored evidence or audit state failed integrity validation."""
