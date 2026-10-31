"""CLI entry point. All live work runs in a separate worker process."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Literal, cast

from pydantic import JsonValue, ValidationError

from . import graphs, ledger
from .cognition import review_receipt
from .domain import GraphInput, LedgerInput, RunSpec, canonical, digest, json_object
from .examples import graph_example, ledger_example
from .providers import ProviderConfig, load_environment
from .service import parse_record, replay
from .storage import Store
from .worker import launch


def default_payload(lab: str, store: Store) -> dict[str, JsonValue]:
    if lab == "ledger":
        return json_object(ledger_example())
    if lab == "graph":
        return json_object(graph_example())
    active = store.active_prompt()
    return {"parent": active} if active else {}


def main() -> None:
    load_environment()
    parser = argparse.ArgumentParser(description="Anomalon Research Workbench 0.0.1.0")
    parser.add_argument("--data", type=Path, default=Path(os.getenv("WORKBENCH_DATA_DIR", "data")))
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "check"):
        sub = commands.add_parser(name)
        sub.add_argument("lab", choices=("ledger", "graph", "revision"))
        sub.add_argument("--input", type=Path)
        if name == "run":
            sub.add_argument(
                "--provider", choices=("anthropic", "openrouter", "compatible", "local")
            )
            sub.add_argument("--model")
            sub.add_argument("--wait", action="store_true")
    commands.add_parser("list")
    commands.add_parser("recover")
    for name in ("show", "cancel", "admit", "review"):
        sub = commands.add_parser(name)
        sub.add_argument("run_id")
        if name == "admit":
            sub.add_argument("--actor", required=True, choices=("operator", "viewer"))
    sub = commands.add_parser("export")
    sub.add_argument("run_id")
    sub.add_argument("output", type=Path)
    sub = commands.add_parser("replay")
    sub.add_argument("bundle", type=Path)
    args = parser.parse_args()
    store = Store(args.data)
    try:
        result: object
        if args.command in ("check", "run"):
            payload = (
                json.loads(args.input.read_text(encoding="utf-8"))
                if args.input
                else default_payload(args.lab, store)
            )
            spec = RunSpec(
                lab=cast(Literal["ledger", "graph", "revision"], args.lab), payload=payload
            )
            if args.command == "check":
                if args.lab == "revision":
                    raise ValueError("Revision requires live generation; use run or replay")
                result = (
                    ledger.evaluate(parse_record(canonical(payload), LedgerInput))
                    if args.lab == "ledger"
                    else graphs.evaluate(parse_record(canonical(payload), GraphInput))
                )
            else:
                config = ProviderConfig.from_env(args.provider, args.model)
                store.recover()
                run_id = store.enqueue(uuid.uuid4().hex, json_object(spec), config.public())
                launch(store, run_id)
                if args.wait:
                    while store.get(run_id)["status"] in ("queued", "running"):
                        time.sleep(0.25)
                        store.recover()
                result = store.get(run_id)
                if args.wait and result["status"] != "completed":
                    print(canonical(result))
                    sys.exit(1)
        elif args.command == "list":
            result = store.list_runs()
        elif args.command == "recover":
            result = {"interrupted": store.recover()}
        elif args.command == "cancel":
            store.cancel(args.run_id)
            result = store.get(args.run_id)
        elif args.command == "admit":
            result = {"admitted_prompt": store.admit(args.run_id, args.actor)}
        elif args.command in ("show", "review"):
            row = store.get(args.run_id)
            result = store.read(str(row["receipt_hash"])) if row["receipt_hash"] else row
            if args.command == "review":
                result = review_receipt(result)
        elif args.command == "export":
            row = store.get(args.run_id)
            receipt = store.read(str(row["receipt_hash"]))
            bundle = {"sha256": digest(receipt), "receipt": receipt}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(canonical(bundle), encoding="utf-8")
            result = {"exported": str(args.output)}
        else:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
            valid = digest(bundle["receipt"]) == bundle["sha256"] and replay(bundle["receipt"])
            result = {"integrity_and_semantic_replay": valid}
            if not valid:
                print(canonical(result))
                sys.exit(1)
        print(canonical(result))
    except (ValueError, ValidationError, OSError, KeyError):
        print(
            canonical(
                {
                    "error": "Invalid input, configuration, artifact or operation. Check the command and scoped settings."
                }
            )
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
