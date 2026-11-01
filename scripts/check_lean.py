"""Check the pinned supplement and write a source-bound verification record."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "lean"
NAMES = [
    "witness_membership",
    "observation_ambiguity",
    "no_total_decider",
    "extra_observation_suffices",
]
ALLOWED = {"propext", "Quot.sound", "Classical.choice"}


def main() -> None:
    version = subprocess.run(
        ["lean", "--version"], cwd=LEAN, capture_output=True, encoding="utf-8", timeout=60
    )
    checked = subprocess.run(
        ["lean", "Ledger.lean"], cwd=LEAN, capture_output=True, encoding="utf-8", timeout=60
    )
    output = checked.stdout + checked.stderr
    declarations = {}
    for name in NAMES:
        match = re.search(
            r"'AnomalonLedger\." + name + r"' depends on axioms: \[([^\]]*)\]", output
        )
        no_axioms = f"'AnomalonLedger.{name}' does not depend on any axioms" in output
        if not match and not no_axioms:
            raise RuntimeError(f"Missing axiom audit: {name}\n{output}")
        axioms = {s.strip() for s in match[1].split(",") if s.strip()} if match else set()
        if not axioms <= ALLOWED:
            raise RuntimeError("Undeclared axiom dependency")
        declarations[name] = sorted(axioms)
    if checked.returncode or version.returncode or "4.19.0" not in version.stdout:
        raise RuntimeError(output + version.stdout)
    files = ["Ledger.lean", "lean-toolchain", "lakefile.toml"]
    report = {
        "status": "checked",
        "toolchain": version.stdout.strip(),
        "source_sha256": {f: hashlib.sha256((LEAN / f).read_bytes()).hexdigest() for f in files},
        "axioms": declarations,
        "output": output,
        "scope": "Four named finite-ledger results only; not evidence truth or authorization",
    }
    destination = ROOT / "evidence" / "lean-verification.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Four named Lean results checked; source-bound axiom audit written.")


if __name__ == "__main__":
    main()
