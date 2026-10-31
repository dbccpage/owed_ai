"""One bounded application service shared by worker, CLI, UI and replay."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import TypeVar, cast

from pydantic import JsonValue, ValidationError

from . import graphs, ledger
from .cognition import review
from .comparison import checklist
from .domain import (
    CORE,
    POLICY_VERSION,
    VERSION,
    GraphInput,
    LedgerInput,
    ModelProvider,
    ModelReply,
    PromptRevision,
    PromptVersion,
    Proposal,
    ProviderFailure,
    Record,
    RunSpec,
    canonical,
    digest,
    json_object,
)
from .examples import initial_prompt, revision_cases

R = TypeVar("R", bound=Record)
LEDGER_MODEL = "S={(a,100-a): integer a in [0,120]}. Target: a>=0 and b>=0. Observations apply only to matching units and snapshot. In this ledger task repairs MUST be an empty array. Request missing or corrected evidence using evidence_requests; you cannot repair or replace observations."


def unique_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def parse_record[R: Record](text: str, record: type[R]) -> R:
    value = json.loads(text, object_pairs_hook=unique_object)
    return record.model_validate_json(canonical(value))


class Runtime:
    def __init__(
        self,
        provider: ModelProvider,
        spec: RunSpec,
        emit: Callable[[dict[str, JsonValue]], None] = lambda event: None,
        cancelled: Callable[[], bool] = lambda: False,
    ):
        self.provider = provider
        self.spec = spec
        self.emit = emit
        self.cancelled = cancelled
        self.started = time.monotonic()
        self.calls: list[dict[str, JsonValue]] = []

    def check(self) -> None:
        if self.cancelled():
            raise ProviderFailure("cancelled")
        if time.monotonic() - self.started >= self.spec.limits.seconds:
            raise ProviderFailure("time_budget_exhausted")

    def ask(self, system: str, user: str, kind: type[R]) -> R:
        self.check()
        if len(self.calls) >= self.spec.limits.requests:
            raise ProviderFailure("request_budget_exhausted")
        if len(system) + len(user) > 32000:
            raise ProviderFailure("input_size_limit")
        request: dict[str, JsonValue] = {
            "system": system,
            "user": user,
            "schema": kind.model_json_schema(),
            "max_tokens": self.spec.limits.output_tokens,
        }
        call: dict[str, JsonValue] = {"request": request, "request_hash": digest(request)}
        self.calls.append(call)
        self.emit(
            {"kind": "request_started", "index": len(self.calls), "request_hash": digest(request)}
        )
        try:
            reply = self.provider.generate(
                system,
                user,
                kind.model_json_schema(),
                self.spec.limits.output_tokens,
                min(60.0, self.spec.limits.seconds - (time.monotonic() - self.started)),
            )
            call["reply"] = json_object(reply)
            self.check()
            parsed = parse_record(reply.content, kind)
            self.emit(
                {
                    "kind": "response_validated",
                    "index": len(self.calls),
                    "response_hash": digest(reply),
                }
            )
            return parsed
        except (ValidationError, ValueError):
            call["error"] = "invalid_model_json"
            raise ProviderFailure("invalid_model_json") from None
        except ProviderFailure as exc:
            call["error"] = str(exc)
            raise


def evaluate_ledger(runtime: Runtime) -> dict[str, JsonValue]:
    data = parse_record(canonical(runtime.spec.payload), LedgerInput)
    result = ledger.evaluate(data)
    if not ledger.verify(data, result):
        raise ProviderFailure("independent_verifier_disagreement")
    host: dict[str, JsonValue] = {"evaluation": json_object(result)}
    runtime.emit({"kind": "host_evaluation", **host})
    proposal = runtime.ask(
        CORE + "\n" + LEDGER_MODEL,
        canonical({"question": data.claim.question, "input": json_object(data)}),
        Proposal,
    )
    host["proposal"] = json_object(proposal)
    host["proposal_agrees"] = proposal.verdict == result.verdict.value
    host["comparison"] = {
        "proof_promotion": "supported" if result.total_checked else "not_evaluated",
        "checklist": checklist(data).value,
        "executable_obligations": result.verdict.value,
        "checklist_note": "Fixed engineer-authored checklist uses exact compatibility rules; no superiority claim.",
    }
    return host


def evaluate_graph(runtime: Runtime) -> dict[str, JsonValue]:
    data = parse_record(canonical(runtime.spec.payload), GraphInput)
    result = graphs.evaluate(data)
    if result.certificate is not None and not graphs.verify(data, result.certificate):
        raise ProviderFailure("independent_verifier_disagreement")
    host: dict[str, JsonValue] = {"original": json_object(data), "evaluation": json_object(result)}
    runtime.emit({"kind": "host_evaluation", **host})
    proposal = runtime.ask(
        CORE + "\nAn edge means potential(target)-potential(source)=difference. "
        "Propose only edits to editable edges, preserving all others. "
        "Your verdict concerns existence of a global potential.",
        canonical(data),
        Proposal,
    )
    host["proposal"] = json_object(proposal)
    host["proposal_agrees"] = proposal.verdict == result.verdict.value
    if proposal.repairs:
        try:
            child = graphs.repair(data, proposal.repairs)
            checked = graphs.evaluate(child)
            if checked.certificate is not None and not graphs.verify(child, checked.certificate):
                raise ValueError("invalid_repair_certificate")
            host.update(
                {
                    "child": json_object(child),
                    "parent_hash": digest(data),
                    "repair_evaluation": json_object(checked),
                    "repair_authorized": False,
                }
            )
        except (ValueError, ZeroDivisionError):
            host["repair_rejection"] = "Invalid or protected-edge edit"
    return host


def evaluate_revision(runtime: Runtime) -> dict[str, JsonValue]:
    if set(runtime.spec.payload) - {"parent"}:
        raise ValueError("unknown_revision_input")
    parent = (
        parse_record(canonical(runtime.spec.payload["parent"]), PromptVersion)
        if "parent" in runtime.spec.payload
        else initial_prompt()
    )
    cases = revision_cases()
    scores: dict[str, list[dict[str, JsonValue]]] = {"parent": [], "child": []}

    def assess(prompt: PromptVersion, phase: str, index: int) -> dict[str, JsonValue]:
        case_id, data = cases[index]
        answer = runtime.ask(
            prompt.core + "\n" + prompt.instructions + "\n" + LEDGER_MODEL,
            canonical(data),
            Proposal,
        )
        expected = ledger.evaluate(data).verdict.value
        row: dict[str, JsonValue] = {
            "case": case_id,
            "expected": expected,
            "answer": json_object(answer),
            "correct": answer.verdict == expected,
            "split": "development" if index < 2 else "heldout",
        }
        scores[phase].append(row)
        return row

    development = [assess(parent, "parent", i) for i in range(2)]
    revision = runtime.ask(
        CORE + "\nRevise only the editable instructions. "
        "Return instructions and rationale; no other fields. Preserve the protected core.",
        canonical({"parent": json_object(parent), "development_feedback": development}),
        PromptRevision,
    )
    child = PromptVersion(
        instructions=revision.instructions,
        parent_hash=digest(parent),
        mutation=revision.rationale,
        failure_refs=tuple(digest(row) for row in development if not row["correct"]),
    )
    for i in range(2):
        assess(child, "child", i)
    # Held-out evaluation begins only after the child is frozen. Nothing flows back to mutation.
    for i in range(2, 4):
        assess(parent, "parent", i)
        assess(child, "child", i)
    parent_count = sum(r["correct"] is True for r in scores["parent"])
    child_count = sum(r["correct"] is True for r in scores["child"])
    outcome = (
        "improved"
        if child_count > parent_count
        else "tie"
        if child_count == parent_count
        else "regressed"
    )
    return {
        "parent": json_object(parent),
        "child": json_object(child),
        "scores": cast(JsonValue, scores),
        "parent_correct": parent_count,
        "child_correct": child_count,
        "denominator": 4,
        "outcome": outcome,
        "eligible": child_count == 4,
        "admitted": False,
        "scope": "Four frozen synthetic cases; not a generalization claim",
    }


def execute(runtime: Runtime, config: dict[str, JsonValue]) -> dict[str, JsonValue]:
    status = "completed"
    try:
        result = {
            "ledger": evaluate_ledger,
            "graph": evaluate_graph,
            "revision": evaluate_revision,
        }[runtime.spec.lab](runtime)
        runtime.check()
        runtime.emit(
            {"kind": "cognitive_review", "review": json_object(review(runtime.spec, result))}
        )
    except (ProviderFailure, ValueError, ValidationError) as exc:
        status = "cancelled" if str(exc) == "cancelled" else "failed"
        error = str(exc) if isinstance(exc, ProviderFailure) else "invalid_experiment_input"
        result = {"execution_error": error, "model_evaluation": "not_evaluated"}
        # Independent host evidence remains inspectable even when generation fails.
        if runtime.spec.lab == "ledger":
            try:
                data = parse_record(canonical(runtime.spec.payload), LedgerInput)
                result["evaluation"] = json_object(ledger.evaluate(data))
            except (ValueError, ValidationError):
                pass
    except Exception:
        status = "failed"
        result = {
            "execution_error": "checker_or_execution_failed",
            "model_evaluation": "not_evaluated",
            "host_evaluation": "not_evaluated",
        }
    return {
        "version": VERSION,
        "policy_version": POLICY_VERSION,
        "checker_version": VERSION,
        "spec": json_object(runtime.spec),
        "config": config,
        "status": status,
        "result": result,
        "calls": cast(JsonValue, runtime.calls),
        "request_count": len(runtime.calls),
    }


class ReplayProvider:
    def __init__(self, calls: list[dict[str, JsonValue]]):
        self.calls = calls
        self.index = 0

    def generate(
        self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float
    ) -> ModelReply:
        if self.index >= len(self.calls):
            raise ProviderFailure("replay_exhausted")
        call = self.calls[self.index]
        self.index += 1
        request = {"system": system, "user": user, "schema": schema, "max_tokens": max_tokens}
        if digest(request) != call["request_hash"]:
            raise ProviderFailure("replay_request_mismatch")
        if "reply" not in call:
            raise ProviderFailure(str(call.get("error", "missing_reply")))
        return parse_record(canonical(call["reply"]), ModelReply)


def replay(receipt: dict[str, JsonValue]) -> bool:
    spec = parse_record(canonical(receipt["spec"]), RunSpec)
    provider = ReplayProvider(cast(list[dict[str, JsonValue]], receipt["calls"]))
    regenerated = execute(Runtime(provider, spec), cast(dict[str, JsonValue], receipt["config"]))
    return digest(regenerated) == digest(receipt) and provider.index == len(provider.calls)
