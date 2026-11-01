"""Audit the mandatory migration model results; never attest Python/SQL equivalence."""

import hashlib
import json
import subprocess
from pathlib import Path

from anomalon_workbench.migration_proof import MigrationProofReport, audit_migration_output

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    command = ["lean", "Migration.lean"]
    version = subprocess.run(
        ["lean", "--version"], cwd=ROOT / "lean", capture_output=True,
        encoding="utf-8", check=True, timeout=60,
    )
    result = subprocess.run(command, cwd=ROOT / "lean", capture_output=True,
                            encoding="utf-8", timeout=60)
    output = result.stdout + result.stderr
    if result.returncode or "4.19.0" not in version.stdout or "sorry" in output:
        raise RuntimeError(output)
    axioms = audit_migration_output(output)
    report = {
        "status": "verified_during_build",
        "version": version.stdout.strip(),
        "command": command,
        "exit_status": result.returncode,
        "theorems": axioms,
        "source_sha256": {
            str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in ("lean/Migration.lean", "lean/lean-toolchain")
        },
        "assumptions": "Finite permutation for conservation; two-sided inverse authoritative crosswalk for ownership. Synthetic trust is external to these theorems.",
        "boundary": "Model results only; Python and committed SQLite rows require separate runtime checks.",
        "output": output,
    }
    validated = MigrationProofReport.model_validate_json(json.dumps(report))
    (ROOT / "evidence/migration-lean.json").write_text(
        json.dumps(validated.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("Three mandatory migration results checked; axiom audit passed.")


if __name__ == "__main__":
    main()
