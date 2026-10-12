"""Command-line interface: ``python -m integrator {validate,run,runs,errors,connectors}``."""

import argparse
import time

from integrator.config import load_flow
from integrator.connectors import CONNECTORS
from integrator.errors import IntegratorError
from integrator.mapping import validate_mapping
from integrator.runner import run_flow
from integrator.store import Store


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="integrator", description="Run integration flows.")
    p.add_argument("--db", default="integrator.db", help="SQLite file for history/state")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("flow", help="path to a flow JSON file")
    sub.choices["run"].add_argument("--dry-run", action="store_true", help="read and map, do not write")
    sv = sub.add_parser("serve", help="run a flow repeatedly on an interval")
    sv.add_argument("flow")
    sv.add_argument("--every", type=float, required=True, help="seconds between runs")
    sv.add_argument("--max-runs", type=int, default=0, help="stop after N runs (0 = forever)")
    for name in ("runs", "errors"):
        sp = sub.add_parser(name)
        sp.add_argument("--flow")
        sp.add_argument("--limit", type=int, default=20)
    sub.add_parser("connectors")
    args = p.parse_args(argv)

    try:
        if args.cmd == "connectors":
            print("\n".join(sorted(CONNECTORS)))
        elif args.cmd == "validate":
            flow = load_flow(args.flow)
            validate_mapping(flow["mapping"])
            print(f"ok: {flow['name']}")
        elif args.cmd == "run":
            res = run_flow(load_flow(args.flow), Store(args.db), dry_run=args.dry_run)
            print(f"run {res.run_id}: {res.status} read={res.read} written={res.written} failed={res.failed}")
            return 0 if res.status == "success" else 1
        elif args.cmd == "serve":
            flow, store, n = load_flow(args.flow), Store(args.db), 0
            while True:
                try:
                    res = run_flow(flow, store)
                    print(f"run {res.run_id}: {res.status} read={res.read} written={res.written} failed={res.failed}",
                          flush=True)
                except IntegratorError as exc:  # keep the schedule alive across bad runs
                    print(f"error: {exc}", flush=True)
                n += 1
                if args.max_runs and n >= args.max_runs:
                    break
                time.sleep(args.every)
        elif args.cmd == "runs":
            for r in Store(args.db).runs(args.flow, args.limit):
                print("#{} {} {} {} read={} written={} failed={}".format(*r))
        elif args.cmd == "errors":
            for run_id, flow, stage, msg, rec in Store(args.db).errors(args.flow, args.limit):
                print(f"run {run_id} [{flow}] {stage}: {msg}" + (f"\n  {rec}" if rec else ""))
    except IntegratorError as exc:
        print(f"error: {exc}")
        return 2
    return 0
