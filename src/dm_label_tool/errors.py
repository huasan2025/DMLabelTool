"""Custom exceptions for the DM label tool."""


class DMLabelError(Exception):
    """Base error for user-facing failures."""


class ValidationError(DMLabelError):
    """Input validation failure."""


class DependencyError(DMLabelError):
    """Runtime dependency cannot be loaded."""


class GenerationError(DMLabelError):
    """Generation process failed."""

