"""Flow execution: read source -> map -> write destination, with retries and error capture."""

import time
from dataclasses import dataclass

from integrator.config import resolve_env, validate_flow
from integrator.connectors import build
from integrator.errors import ConnectorError, IntegratorError, MappingError
from integrator.mapping import get_path, map_record, validate_mapping
from integrator.store import Store


@dataclass
class RunResult:
    run_id: int
    status: str
    read: int = 0
    written: int = 0
    failed: int = 0


def _batches(iterable, size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _write_with_retry(dest, records, ctx, retries, sleep):
    for attempt in range(retries + 1):
        try:
            return dest.write_batch(records, ctx)
        except ConnectorError as exc:
            if not exc.retryable or attempt == retries:
                raise
            sleep(min(2 ** attempt, 30))


def run_flow(flow: dict, store: Store, *, transport=None, env=None, dry_run=False,
             sleep=time.sleep) -> RunResult:
    flow = validate_flow(flow)
    validate_mapping(flow["mapping"])
    name = flow["name"]
    source = build(resolve_env(flow["source"], env), transport)
    dest = build(resolve_env(flow["destination"], env), transport)

    state = store.get_state(name)
    run_id = store.start_run(name)
    result = RunResult(run_id, "running")
    delta_field = flow["source"].get("delta_field")
    high_water = state.get("watermark")

    try:
        for n, batch in enumerate(_batches(source.read(state), flow["batch_size"]), start=1):
            result.read += len(batch)
            mapped, origin = [], []
            for rec in batch:
                try:
                    mapped.append(map_record(rec, flow["mapping"]))
                    origin.append(rec)
                except MappingError as exc:
                    result.failed += 1
                    store.add_error(run_id, name, "mapping", str(exc), rec)
            failures = []
            if mapped and not dry_run:
                ctx = {"run_id": run_id, "flow": name, "batch": n}
                failures = _write_with_retry(dest, mapped, ctx, flow["retries"], sleep)
            for idx, msg in failures:
                result.failed += 1
                store.add_error(run_id, name, "write", msg, origin[idx])
            result.written += 0 if dry_run else len(mapped) - len(failures)
            if delta_field:
                seen = [str(v) for v in (get_path(r, delta_field, None) for r in origin) if v]
                high_water = max(seen + ([high_water] if high_water else []), default=high_water)
        result.status = "success" if result.failed == 0 else "partial"
    except IntegratorError as exc:
        result.status = "failed"
        store.add_error(run_id, name, "run", str(exc))
    finally:
        # Only advance the watermark on a clean run so failed records are re-read next time.
        if result.status == "success" and not dry_run and high_water != state.get("watermark"):
            store.set_state(name, {**state, "watermark": high_water})
        store.finish_run(run_id, result.status, result.read, result.written, result.failed)
    return result

