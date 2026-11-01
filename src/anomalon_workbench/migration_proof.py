"""Validate complete source-bound build evidence; never compile Lean in a public run."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, JsonValue, model_validator

from .domain import Record
from .service import parse_record

TOOLCHAIN = "leanprover/lean4:v4.19.0"
PROOF_SOURCES = {"lean/Migration.lean", "lean/lean-toolchain"}
AXIOM_LIMITS = {
    "conservation": {"propext", "Quot.sound"},
    "insufficient_total": set(),
    "ownership": set(),
}
PROOF_ASSUMPTIONS = "Finite permutation for conservation; two-sided inverse authoritative crosswalk for ownership. Synthetic trust is external to these theorems."
PROOF_BOUNDARY = "Model results only; Python and committed SQLite rows require separate runtime checks."


def audit_migration_output(output: str) -> dict[str, tuple[str, ...]]:
    """Require each statement and exactly one permitted axiom audit per theorem."""
    if re.search(r"\b(sorryAx|sorry|admit)\b", output):
        raise ValueError("proof_placeholder")
    results = {}
    for name, allowed in AXIOM_LIMITS.items():
        qualified = re.escape("OwedMigration." + name)
        if not re.search(r"^" + qualified + r"\b", output, re.MULTILINE):
            raise ValueError("missing_theorem_statement")
        audits = re.findall(
            r"^'" + qualified + r"' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)\s*$",
            output, re.MULTILINE,
        )
        if len(audits) != 1:
            raise ValueError("missing_or_duplicate_theorem_audit")
        used = tuple(sorted(s.strip() for s in audits[0].split(",") if s.strip()))
        if len(set(used)) != len(used) or not set(used) <= allowed:
            raise ValueError("undeclared_axiom")
        results[name] = used
    return results


class MigrationProofReport(Record):
    status: Literal["verified_during_build"]
    version: str = Field(
        pattern=r"^Lean \(version 4\.19\.0, [A-Za-z0-9_-]+, commit [0-9a-f]{12,40}, Release\)$",
        max_length=300,
    )
    command: tuple[Literal["lean"], Literal["Migration.lean"]]
    exit_status: int = Field(ge=0, le=0)
    theorems: dict[str, tuple[str, ...]]
    source_sha256: dict[str, Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]]
    assumptions: str
    boundary: str
    output: str = Field(min_length=1, max_length=50000)

    @model_validator(mode="after")
    def complete(self) -> MigrationProofReport:
        if set(self.source_sha256) != PROOF_SOURCES:
            raise ValueError("required_proof_sources")
        if self.theorems != audit_migration_output(self.output):
            raise ValueError("theorem_audit_mismatch")
        if self.assumptions != PROOF_ASSUMPTIONS or self.boundary != PROOF_BOUNDARY:
            raise ValueError("proof_scope_mismatch")
        return self


def proof_status() -> dict[str, JsonValue]:
    try:
        with Path("evidence/migration-lean.json").open("rb") as handle:
            raw = handle.read(100001)
        if len(raw) > 100000:
            raise ValueError("proof_report_too_large")
        report = parse_record(raw.decode("utf-8"), MigrationProofReport)
        if Path("lean/lean-toolchain").read_text(encoding="utf-8").strip() != TOOLCHAIN:
            raise ValueError("wrong_toolchain")
        if any(
            hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha
            for p, sha in report.source_sha256.items()
        ):
            raise ValueError("stale")
        return {
            "status": "verified_during_build",
            "artifact_sha256": hashlib.sha256(raw).hexdigest(),
            "boundary": report.boundary,
        }
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return {"status": "not_verified_for_this_build"}
