"""A separate bounded worker; reruns cannot claim an already-running job."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from .domain import ModelProvider, RunSpec, canonical
from .hosting import HostedPolicy, Principal, data_root, hosted_mode, private_store
from .providers import HTTPProvider, ProviderConfig, load_environment
from .service import Runtime, execute, parse_record
from .spending import MeteredProvider, SpendLedger
from .storage import Store


def launch(store: Store, run_id: str) -> subprocess.Popen[bytes]:
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    else:
        flags = 0
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
        if hosted_mode() and store.get(run_id)["status"] == "cancelled":
            SpendLedger(data_root() / "control").release_run(run_id)
        return
    watchdog: threading.Timer | None = None
    spending: SpendLedger | None = None
    try:
        row = store.get(run_id)
        spec = parse_record(canonical(store.read(str(row["spec_hash"]))), RunSpec)
        public = store.read(str(row["config_hash"]))
        config = ProviderConfig.restore(public)
        provider: ModelProvider = HTTPProvider(config)
        if hosted_mode():
            spending = SpendLedger(data_root() / "control")
            policy = HostedPolicy.from_env()
            principal = Principal.model_validate(public.get("hosted"))
            if (
                not policy.permits(principal) or private_store(principal).root != store.root
                or config.public() != policy.provider().public()
                or spec.limits.requests > 12 or spec.limits.seconds > 300
                or spec.limits.output_tokens > 2048
            ):
                raise ValueError("invalid_hosted_worker_context")
            provider = MeteredProvider(provider, spending, run_id, principal)

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
            if spending is not None:
                spending.release_run(run_id)
            # A daemon watchdog bounds even a stuck HTTP library; never retries an uncertain call.
            os._exit(1)

        watchdog = threading.Timer(spec.limits.seconds, deadline)
        watchdog.daemon = True
        watchdog.start()
        runtime = Runtime(
            provider,
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
        if spending is not None:
            spending.release_run(run_id)
        if watchdog is not None:
            watchdog.cancel()


if __name__ == "__main__":
    work(Path(sys.argv[1]), sys.argv[2])
