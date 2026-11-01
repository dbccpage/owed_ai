"""Read source-bound build proof evidence without invoking Lean in a public run."""

import hashlib
import json
from pathlib import Path

from pydantic import JsonValue


def proof_status() -> dict[str, JsonValue]:
    try:
        report = json.loads(Path("evidence/migration-lean.json").read_text(encoding="utf-8"))
        if report["exit_status"] != 0 or report["status"] != "verified_during_build":
            raise ValueError("not_checked")
        if not all(
            hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha
            for p, sha in report["source_sha256"].items()
        ):
            raise ValueError("stale")
        return {
            "status": "verified_during_build",
            "artifact_sha256": hashlib.sha256(
                Path("evidence/migration-lean.json").read_bytes()
            ).hexdigest(),
            "boundary": report["boundary"],
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "not_verified_for_this_build"}
