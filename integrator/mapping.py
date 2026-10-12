"""Field mapping: turn a source record into a destination record."""

from integrator.errors import ConfigError, MappingError

_MISSING = object()

TRANSFORMS = {
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "strip": lambda v: str(v).strip(),
    "str": str,
    "int": lambda v: int(float(v)),
    "float": float,
}


def get_path(record, path: str, default=_MISSING):
    """Read a dotted path (``a.b.0.c``) from nested dicts/lists."""
    cur = record
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def validate_mapping(mapping: dict) -> None:
    fields = (mapping or {}).get("fields")
    if fields is None:
        return
    for target, spec in fields.items():
        if isinstance(spec, dict):
            if not ({"from", "const"} & spec.keys()):
                raise ConfigError(f"mapping '{target}' needs 'from' or 'const'")
            for name in _as_list(spec.get("transform")):
                if name not in TRANSFORMS:
                    raise ConfigError(f"mapping '{target}': unknown transform '{name}'")
        elif not isinstance(spec, str):
            raise ConfigError(f"mapping '{target}' must be a path string or an object")


def _as_list(value):
    return [] if value is None else value if isinstance(value, list) else [value]


def map_record(record: dict, mapping: dict) -> dict:
    """Apply ``mapping['fields']``; with no fields configured the record passes through."""
    fields = (mapping or {}).get("fields")
    if fields is None:
        return dict(record)
    out = {}
    for target, spec in fields.items():
        spec = {"from": spec} if isinstance(spec, str) else spec
        if "const" in spec:
            value = spec["const"]
        else:
            value = get_path(record, spec["from"])
            if value is _MISSING or value is None:
                if "default" in spec:
                    value = spec["default"]
                elif spec.get("required"):
                    raise MappingError(f"required field '{spec['from']}' is missing")
                else:
                    value = None
        if value is not None:
            for name in _as_list(spec.get("transform")):
                try:
                    value = TRANSFORMS[name](value)
                except (ValueError, TypeError) as exc:
                    raise MappingError(f"{target}: transform '{name}' failed on {value!r}") from exc
        _set_path(out, target, value)
    return out


def _set_path(out: dict, path: str, value) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        out = out.setdefault(part, {})
    out[parts[-1]] = value
