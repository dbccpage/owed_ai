"""Publish only validation metadata; leave tenant receipts and databases private."""

import argparse
import json
from pathlib import Path

from anomalon_workbench.domain import digest
from anomalon_workbench.service import replay
from anomalon_workbench.spending import SpendLedger
from anomalon_workbench.storage import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    results, usage = [], []
    for path in sorted((args.root / "users").glob("*")):
        store = Store(path)
        usage.append(SpendLedger(args.root / "control").usage(path.name))
        for row in store.list_runs():
            if not row["receipt_hash"]:
                continue
            receipt = store.read(row["receipt_hash"])
            replies = [c["reply"] for c in receipt.get("calls", []) if "reply" in c]
            result = receipt["result"]
            results.append({
                "lab": receipt["spec"]["lab"], "status": row["status"],
                "receipt_sha256": digest(receipt), "replay_matched": replay(receipt),
                "requests": len(receipt["calls"]),
                "reported_cost_usd": sum(r["cost"] for r in replies) if all(r["cost"] is not None for r in replies) else None,
                "parent_correct": result.get("parent_correct"),
                "child_correct": result.get("child_correct"), "outcome": result.get("outcome"),
                "admitted": result.get("admitted"),
            })
    report = {
        "scope": "Local signed-token OIDC fixture + real browser + real OpenRouter worker requests; not a Google/Render/DNS validation",
        "results": sorted(results, key=lambda r: r["lab"]),
        "operator_usage": usage,
        "private_data_exported": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
