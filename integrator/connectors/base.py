"""Connector interface."""

from integrator.errors import ConnectorError
from integrator.http import Transport, UrllibTransport


class Connector:
    """A connector may implement ``read`` (source), ``write_batch`` (destination), or both."""

    def __init__(self, config: dict, transport: Transport | None = None):
        self.config = config
        self.transport = transport or UrllibTransport()
        self.state_update: dict = {}  # merged into saved flow state after a clean run

    def read(self, state: dict):
        """Yield source records (dicts). ``state`` holds the flow's saved watermark."""
        raise ConnectorError(f"{self.config['type']} cannot be used as a source")

    def write_batch(self, records: list[dict], ctx: dict) -> list[tuple[int, str]]:
        """Write records. Return ``(index, message)`` for each record that failed individually;
        raise ConnectorError for a whole-batch failure."""
        raise ConnectorError(f"{self.config['type']} cannot be used as a destination")

    def require(self, *keys):
        missing = [k for k in keys if not self.config.get(k)]
        if missing:
            from integrator.errors import ConfigError
            raise ConfigError(f"{self.config['type']} connector missing: {', '.join(missing)}")
