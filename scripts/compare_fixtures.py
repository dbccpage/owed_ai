"""Freeze raw case outcomes and comparison counts, without claiming superiority."""

import json
from pathlib import Path

from anomalon_workbench.comparison import checklist
from anomalon_workbench.domain import LedgerInput, canonical, digest
from anomalon_workbench.ledger import evaluate, verify
from anomalon_workbench.service import parse_record

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = json.loads((ROOT / "fixtures/ledger.json").read_text())
    rows = []
    for case in cases:
        data = parse_record(json.dumps(case["input"]), LedgerInput)
        result = evaluate(data)
        row = {
            "id": case["id"],
            "expected": case["verdict"],
            "proof_promotion": "supported" if result.total_checked else "not_evaluated",
            "checklist": checklist(data).value,
            "executable": result.verdict.value,
            "authorized": result.authorization.allowed,
            "witnesses_checked": verify(data, result),
        }
        if (
            row["executable"] != case["verdict"]
            or row["authorized"] != case["authorized"]
            or not row["witnesses_checked"]
        ):
            raise AssertionError(case["id"])
        rows.append(row)
    totals = {}
    for condition in ("proof_promotion", "checklist", "executable"):
        totals[condition] = {
            "correct": {
                "numerator": sum(r[condition] == r["expected"] for r in rows),
                "denominator": len(rows),
            },
            "unsupported_acceptance": {
                "numerator": sum(
                    r[condition] == "supported" and r["expected"] != "supported" for r in rows
                ),
                "denominator": sum(r["expected"] != "supported" for r in rows),
            },
        }
        for label in ("supported", "refuted", "underdetermined", "inconsistent", "not_evaluated"):
            totals[condition][label] = {
                "numerator": sum(r[condition] == label and r["expected"] == label for r in rows),
                "denominator": sum(r["expected"] == label for r in rows),
            }
    report = {
        "cases": rows,
        "metrics": totals,
        "fixture_sha256": digest(cases),
        "interpretation": "The independent checklist and executable obligations agree on these finite cases. No superiority claim.",
        "additional_acceptance": "Premise injection, receipt tampering, checker timeout/crash and provider failure are asserted in tests/test_runs.py and tests/test_checkers.py.",
    }
    (ROOT / "evidence/fixture-comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(canonical(totals))


if __name__ == "__main__":
    main()
