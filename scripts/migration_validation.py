"""Reproduce the first migration increment; produces receipts and measured timings."""

import json
import platform
import time
from pathlib import Path

from anomalon_workbench.migration import Observation
from anomalon_workbench.migration_demo import SyntheticAuthority, export, fixture, replay, run
from anomalon_workbench.migration_proof import proof_status


def main() -> None:
    destination = Path("examples/migration")
    destination.mkdir(parents=True, exist_ok=True)
    scenario, original, truth = fixture()
    timings = {}
    for mode in ("repaired", "unresolved", "conflicting"):
        authority = SyntheticAuthority(scenario, truth, "missing" if mode == "unresolved" else "valid")
        initial = (Observation(scope=scenario.scope, links=truth.links),
                   Observation(scope=scenario.scope, links=original.links)) if mode == "conflicting" else ()
        start = time.perf_counter()
        receipt = run(scenario, original, authority, initial)
        timings[mode] = time.perf_counter() - start
        bundle = export(receipt)
        if not replay(bundle):
            raise RuntimeError("replay_failed")
        (destination / (mode + ".json")).write_text(bundle + "\n", encoding="utf-8", newline="\n")
    report = {"environment": platform.platform(), "python": platform.python_version(),
              "accounts": 3, "seconds": timings, "formal_artifact": proof_status(),
              "scope": "Three local core runs; not browser usability or Render cold-start measurements"}
    Path("evidence/migration-core.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
