"""Exception types shared across the integrator."""


class IntegratorError(Exception):
    """Base class for all integrator errors."""


class ConfigError(IntegratorError):
    """A flow or connector configuration is invalid."""


class ConnectorError(IntegratorError):
    """A connector call failed. ``retryable`` marks transient failures (429/5xx/network)."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class MappingError(IntegratorError):
    """A single record could not be mapped."""
