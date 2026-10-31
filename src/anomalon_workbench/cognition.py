"""A bounded cognitive review: make contradictions and next checks easy to inspect.

This audits structured evidence boundaries, not psychology or truth of arbitrary prose.
It is a companion assessment and never rewrites the original receipt or grants authority.
"""

from __future__ import annotations

from typing import cast

from pydantic import JsonValue

from .domain import Record, RunSpec, digest


class ReviewSignal(Record):
    code: str
    detail: str


class CognitiveReview(Record):
    version: str = "cognitive-review/1"
    source_hash: str
    question: str
    checked_result: str
    signals: tuple[ReviewSignal, ...]
    next_check: str
    scope: str = "Structured proposal/evidence comparison only; not a validated human-cognition or general hallucination detector"


def review(spec: RunSpec, result: dict[str, JsonValue]) -> CognitiveReview:
    signals: list[ReviewSignal] = []
    question = {
        "ledger": "Are both reserves nonnegative?",
        "graph": "Do these constraints admit a global solution?",
        "revision": "Did the child improve, and is it eligible for human review?",
    }[spec.lab]
    next_check = "Inspect the bound evidence and its declared scope."
    checked = "not_evaluated"
    if "execution_error" in result:
        signals.append(
            ReviewSignal(
                code="incomplete_execution",
                detail="The model or checker did not complete. This is not a mathematical refutation.",
            )
        )
        next_check = (
            "Resolve the recorded execution error before treating the proposal as evaluated."
        )
    if spec.lab in ("ledger", "graph") and isinstance(result.get("evaluation"), dict):
        evaluation = cast(dict[str, JsonValue], result["evaluation"])
        checked = str(evaluation["verdict"])
        proposal = result.get("proposal")
        if isinstance(proposal, dict):
            if proposal.get("verdict") != checked:
                signals.append(
                    ReviewSignal(
                        code="verdict_mismatch",
                        detail=f"The model proposed {proposal.get('verdict')}; the host checked {checked}.",
                    )
                )
            if proposal.get("verdict") == "supported" and checked != "supported":
                signals.append(
                    ReviewSignal(
                        code="unsupported_certainty",
                        detail="The proposal asserts support that the compatible evidence does not establish.",
                    )
                )
            if spec.lab == "ledger" and proposal.get("repairs"):
                signals.append(
                    ReviewSignal(
                        code="observation_replacement",
                        detail="A model-proposed repair cannot replace an accepted observation.",
                    )
                )
        if spec.lab == "ledger":
            obligations = cast(list[dict[str, JsonValue]], evaluation.get("obligations", []))
            unresolved = [o for o in obligations if o["state"] in ("open", "failed")]
            if unresolved:
                next_check = str(unresolved[0]["evidence_needed"])
            elif checked == "supported":
                next_check = (
                    "Check the separate actor and authorization decision before simulated release."
                )
        elif checked == "refuted":
            next_check = "Inspect the nonzero cycle residual, then verify a new version changing only editable constraints."
        elif checked == "supported":
            next_check = "Inspect the potential certificate and verify that the declared graph represents the intended problem."
        if result.get("repair_rejection"):
            signals.append(
                ReviewSignal(code="invalid_repair", detail=str(result["repair_rejection"]))
            )
    elif spec.lab == "revision" and "outcome" in result:
        checked = str(result["outcome"])
        if checked in ("tie", "regressed"):
            signals.append(
                ReviewSignal(
                    code="no_measured_improvement",
                    detail=f"Parent {result['parent_correct']}/{result['denominator']}; child {result['child_correct']}/{result['denominator']}. Do not describe this as improvement.",
                )
            )
        next_check = (
            "Inspect the failed case rows before proposing another revision."
            if result.get("eligible") is not True
            else "Review the frozen candidate and evaluation; admission remains a separate human decision."
        )
    return CognitiveReview(
        source_hash=digest({"spec": spec.model_dump(mode="json"), "result": result}),
        question=question,
        checked_result=checked,
        signals=tuple(signals),
        next_check=next_check,
    )


def review_receipt(receipt: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Bind an independent review to an unchanged semantic receipt."""
    from .domain import canonical

    spec = RunSpec.model_validate_json(canonical(receipt["spec"]))
    result = cast(dict[str, JsonValue], receipt["result"])
    return {
        "receipt_sha256": digest(receipt),
        "review": review(spec, result).model_dump(mode="json"),
    }
