"""A separate bounded worker; reruns cannot claim an already-running job."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from .domain import RunSpec, canonical
from .providers import HTTPProvider, ProviderConfig, load_environment
from .service import Runtime, execute, parse_record
from .storage import Store


def launch(store: Store, run_id: str) -> subprocess.Popen[bytes]:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.Popen(
        [sys.executable, "-m", "anomalon_workbench.worker", str(store.root), run_id],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )


def work(root: Path, run_id: str) -> None:
    load_environment()
    store = Store(root)
    if not store.claim(run_id, os.getpid()):
        return
    watchdog: threading.Timer | None = None
    try:
        row = store.get(run_id)
        spec = parse_record(canonical(store.read(str(row["spec_hash"]))), RunSpec)
        public = store.read(str(row["config_hash"]))
        config = ProviderConfig.restore(public)

        def deadline() -> None:
            store.finish(
                run_id,
                "failed",
                {
                    "status": "failed",
                    "spec": spec.model_dump(mode="json"),
                    "config": public,
                    "result": {
                        "execution_error": "worker_deadline_exceeded",
                        "model_evaluation": "not_evaluated",
                    },
                },
            )
            # A daemon watchdog bounds even a stuck HTTP library; never retries an uncertain call.
            os._exit(1)

        watchdog = threading.Timer(spec.limits.seconds, deadline)
        watchdog.daemon = True
        watchdog.start()
        runtime = Runtime(
            HTTPProvider(config),
            spec,
            lambda event: store.event(run_id, event),
            lambda: store.cancelled(run_id),
        )
        receipt = execute(runtime, public)
        store.finish(run_id, str(receipt["status"]), receipt)
    except Exception:
        # Do not serialize exception text: HTTP exceptions can contain credentials or inputs.
        store.finish(
            run_id,
            "failed",
            cast(
                dict[str, JsonValue],
                {
                    "status": "failed",
                    "result": {
                        "execution_error": "worker_failed",
                        "model_evaluation": "not_evaluated",
                    },
                },
            ),
        )
    finally:
        if watchdog is not None:
            watchdog.cancel()


if __name__ == "__main__":
    work(Path(sys.argv[1]), sys.argv[2])
