"""Typed failures. Each one fails closed at a specific place — no error
here ever routes a review to a different backend."""


class ReviewerError(Exception):
    """Base for every reviewer error."""


class ConfigError(ReviewerError):
    """The reviewer configuration is invalid. Refuse to start."""


class ReviewerUnavailable(ReviewerError):
    """The backend cannot run here, now (daemon down, CLI absent, not
    logged in, timeout)."""


class ModelUnavailable(ReviewerError):
    """The backend is up but the configured model is not installed."""


class MalformedResponse(ReviewerError):
    """The reviewer answered, but not in the structured shape required."""
