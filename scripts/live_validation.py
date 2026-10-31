"""Explicit, bounded live validation; prints metadata only, never keys or HTTP errors."""

import argparse
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

from anomalon_workbench.cognition import review_receipt
from anomalon_workbench.domain import RunSpec, canonical, digest, json_object
from anomalon_workbench.examples import graph_example, ledger_example
from anomalon_workbench.providers import ProviderConfig, load_environment
from anomalon_workbench.service import replay
from anomalon_workbench.storage import Store
from anomalon_workbench.worker import launch

ROOT = Path(__file__).resolve().parents[1]


def run_case(store, config, spec):
    """Exercise the same queue, separate process, persistence and replay as the application."""
    run_id = store.enqueue(uuid.uuid4().hex, json_object(spec), config.public())
    started = time.monotonic()
    print(canonical({"lab": spec.lab, "run_id": run_id, "status": "queued"}), flush=True)
    child = launch(store, run_id)
    try:
        while store.get(run_id)["status"] in ("queued", "running"):
            if child.poll() is not None:
                break
            if time.monotonic() - started > spec.limits.seconds + 15:
                store.cancel(run_id)
                raise RuntimeError("validation_worker_deadline")
            time.sleep(0.2)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
    row = store.get(run_id)
    if not row["receipt_hash"]:
        raise RuntimeError("worker_exited_without_receipt")
    receipt = store.read(row["receipt_hash"])
    matched = replay(receipt) if "calls" in receipt else False
    events = store.events(run_id)
    replies = [c["reply"] for c in receipt.get("calls", []) if "reply" in c]
    costs = [r.get("cost") for r in replies]
    report = {
        "lab": spec.lab,
        "run_id": run_id,
        "status": row["status"],
        "worker_exit_code": child.returncode,
        "requests": receipt.get("request_count", len(receipt.get("calls", []))),
        "replay_matched": matched,
        "receipt_sha256": digest(receipt),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "progress_event_count": len(events),
        "cognitive_review_recorded": any(e.get("kind") == "cognitive_review" for e in events),
        "reported_input_tokens": sum(r.get("input_tokens") or 0 for r in replies),
        "reported_output_tokens": sum(r.get("output_tokens") or 0 for r in replies),
        "reported_cost_usd": sum(costs) if costs and all(c is not None for c in costs) else None,
        "execution_error": receipt["result"].get("execution_error"),
    }
    return receipt, report


def successful(reports):
    return bool(reports) and all(
        r["status"] == "completed" and r["replay_matched"] for r in reports
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=["anthropic", "openrouter"])
    parser.add_argument("--model")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--lab", choices=["all", "ledger", "graph", "revision"], default="all")
    args = parser.parse_args()
    load_environment(ROOT / ".env")
    config = ProviderConfig.from_env(args.provider, args.model or "discovery-only")
    if args.list_models:
        headers = (
            {"x-api-key": config.key, "anthropic-version": "2023-06-01"}
            if args.provider == "anthropic"
            else {"Authorization": "Bearer " + config.key}
        )
        try:
            response = httpx.get(config.base_url + "/models", headers=headers, timeout=30)
            if response.status_code != 200:
                print("Model discovery HTTP status:", response.status_code)
                return
            print(json.dumps([item["id"] for item in response.json()["data"]]))
        except (httpx.HTTPError, ValueError, KeyError):
            print("Model discovery failed; no response body disclosed.")
        return
    if not args.model:
        parser.error("--model required for live requests")
    attempt = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "examples" / "attempts" / args.provider / attempt
    folder.mkdir(parents=True, exist_ok=False)
    live = ROOT / "examples" / "live" / args.provider
    live.mkdir(parents=True, exist_ok=True)
    store = Store(args.data)
    store.recover()
    reports = []
    for lab, payload in (
        ("ledger", json_object(ledger_example())),
        ("graph", json_object(graph_example())),
        ("revision", {}),
    ):
        if args.lab not in ("all", lab):
            continue
        spec = RunSpec(lab=lab, payload=payload)
        receipt, report = run_case(store, config, spec)
        bundle = {"sha256": digest(receipt), "receipt": receipt}
        (folder / (lab + ".json")).write_text(canonical(bundle), encoding="utf-8")
        if report["status"] == "completed" and report["replay_matched"]:
            (live / (lab + ".json")).write_text(canonical(bundle), encoding="utf-8")
        if "spec" in receipt:
            (folder / (lab + "-review.json")).write_text(
                canonical(review_receipt(receipt)), encoding="utf-8"
            )
        reports.append(report)
        print(canonical(report), flush=True)
        if report["execution_error"] in ("authentication_failed", "unsupported_request_or_model"):
            break
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    complete = successful(reports) and len(reports) == (3 if args.lab == "all" else 1)
    summary = {
        "attempt": attempt,
        "provider": config.public(),
        "results": reports,
        "requested_lab": args.lab,
        "requested_scope_passed": complete,
        "execution_path": "SQLite queue -> separate Python worker -> provider -> persisted receipt -> offline replay",
        "scope": "These recorded runs only; fresh generation is nondeterministic. Unattempted labs are not validated.",
    }
    serialized = json.dumps(summary, indent=2) + "\n"
    (folder / "summary.json").write_text(serialized, encoding="utf-8")
    (evidence / (args.provider + "-live.json")).write_text(serialized, encoding="utf-8")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
