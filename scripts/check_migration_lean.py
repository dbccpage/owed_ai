"""Audit the mandatory migration model results; never attest Python/SQL equivalence."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    command = ["lean", "Migration.lean"]
    version = subprocess.run(
        ["lean", "--version"], cwd=ROOT / "lean", capture_output=True, text=True, check=True
    )
    result = subprocess.run(command, cwd=ROOT / "lean", capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode or "4.19.0" not in version.stdout or "sorry" in output:
        raise RuntimeError(output)
    axioms = {}
    for name in ("conservation", "insufficient_total", "ownership"):
        match = re.search(r"'OwedMigration\." + name + r"' depends on axioms: \[([^\]]*)\]", output)
        empty = f"'OwedMigration.{name}' does not depend on any axioms" in output
        if not match and not empty:
            raise RuntimeError("missing_theorem_audit")
        used = sorted(s.strip() for s in match[1].split(",") if s.strip()) if match else []
        if not set(used) <= {"propext", "Quot.sound", "Classical.choice"}:
            raise RuntimeError("undeclared_axiom")
        axioms[name] = used
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
    (ROOT / "evidence/migration-lean.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print("Three mandatory migration results checked; axiom audit passed.")


if __name__ == "__main__":
    main()
