"""Flow-file loading. Secrets are never stored in flow files: use ``$env:NAME`` references."""

import json
import os
import re

from integrator.errors import ConfigError

_ENV_REF = re.compile(r"^\$env:([A-Za-z_][A-Za-z0-9_]*)$")


def resolve_env(value, env=None):
    """Recursively replace ``"$env:NAME"`` strings with the environment variable's value."""
    env = os.environ if env is None else env
    if isinstance(value, str):
        m = _ENV_REF.match(value)
        if m:
            if m.group(1) not in env:
                raise ConfigError(f"environment variable {m.group(1)} is not set")
            return env[m.group(1)]
        return value
    if isinstance(value, dict):
        return {k: resolve_env(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env(v, env) for v in value]
    return value


def load_flow(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            flow = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read flow {path}: {exc}") from exc
    return validate_flow(flow)


def validate_flow(flow: dict) -> dict:
    if not isinstance(flow, dict):
        raise ConfigError("flow must be a JSON object")
    for key in ("name", "source", "destination"):
        if key not in flow:
            raise ConfigError(f"flow is missing required key '{key}'")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(flow["name"])):
        raise ConfigError("flow name may only contain letters, digits, '_', '.', '-'")
    for side in ("source", "destination"):
        if not isinstance(flow[side], dict) or "type" not in flow[side]:
            raise ConfigError(f"flow.{side} must be an object with a 'type'")
    flow.setdefault("mapping", {"fields": None})
    flow.setdefault("batch_size", 100)
    flow.setdefault("retries", 3)
    if not isinstance(flow["batch_size"], int) or flow["batch_size"] < 1:
        raise ConfigError("batch_size must be a positive integer")
    if not isinstance(flow["retries"], int) or flow["retries"] < 0:
        raise ConfigError("retries must be a non-negative integer")
    return flow
