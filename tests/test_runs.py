import json
import time

import pytest

from anomalon_workbench.domain import (
    CORE,
    Limits,
    ModelReply,
    PromptVersion,
    ProviderFailure,
    RunSpec,
    canonical,
    digest,
    json_object,
)
from anomalon_workbench.examples import graph_example, ledger_example
from anomalon_workbench.service import Runtime, execute, parse_record, replay
from anomalon_workbench.storage import Store


class Scripted:
    """Explicit test double, never presented as a live model."""

    def __init__(self, contents):
        self.contents = iter(contents)
        self.requests = []

    def generate(self, system, user, schema, max_tokens, timeout):
        self.requests.append((system, user))
        value = next(self.contents)
        if isinstance(value, Exception):
            raise value
        return ModelReply(content=json.dumps(value))


def answer(verdict, **extra):
    return {"interpretation": "Test proposal", "verdict": verdict, **extra}


def revision_provider():
    return Scripted(
        [
            answer("underdetermined"),
            answer("supported"),
            {
                "instructions": "Check scope and compatible states.",
                "rationale": "Explicit obligations",
            },
            answer("underdetermined"),
            answer("supported"),
            answer("refuted"),
            answer("refuted"),
            answer("inconsistent"),
            answer("inconsistent"),
        ]
    )


def test_revision_nine_requests_and_no_leakage():
    provider = revision_provider()
    receipt = execute(
        Runtime(provider, RunSpec(lab="revision", payload={})), {"provider": "test-double"}
    )
    assert receipt["status"] == "completed"
    assert receipt["request_count"] == 9
    result = receipt["result"]
    assert result["outcome"] == "tie"
    assert result["eligible"] is True
    assert result["admitted"] is False
    assert result["child"]["core"] == CORE
    assert result["child"]["parent_hash"] == digest(result["parent"])
    mutation_request = provider.requests[2][1]
    assert "heldout" not in mutation_request
    assert '"value":-20' not in mutation_request
    for i, (_, user) in enumerate(provider.requests):
        if i != 2:
            assert "expected" not in user
    assert replay(receipt)


@pytest.mark.parametrize(
    "lab,payload,reply",
    [
        ("ledger", json_object(ledger_example()), answer("supported", evidence_requests=["b>=0"])),
        (
            "graph",
            json_object(graph_example()),
            answer("refuted", repairs=[{"edge_id": "ac", "difference": "2"}]),
        ),
    ],
)
def test_proposals_and_replay(lab, payload, reply):
    receipt = execute(Runtime(Scripted([reply]), RunSpec(lab=lab, payload=payload)), {})
    assert receipt["status"] == "completed"
    assert replay(receipt)
    if lab == "ledger":
        assert receipt["result"]["evaluation"]["verdict"] == "underdetermined"
        assert receipt["result"]["proposal_agrees"] is False
    else:
        assert receipt["result"]["original"]["edges"][-1]["difference"] == "3"
        assert receipt["result"]["repair_evaluation"]["verdict"] == "supported"
    receipt["calls"][0]["request_hash"] = "0" * 64
    assert not replay(receipt)


def test_failure_cancel_and_budget():
    spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
    failed = execute(Runtime(Scripted([ProviderFailure("provider_timeout")]), spec), {})
    assert failed["status"] == "failed"
    assert failed["result"]["evaluation"]["verdict"] == "underdetermined"
    assert failed["result"]["model_evaluation"] == "not_evaluated"
    assert replay(failed)
    cancelled = execute(Runtime(Scripted([]), spec, cancelled=lambda: True), {})
    assert cancelled["status"] == "cancelled"
    assert cancelled["request_count"] == 0
    short = RunSpec(lab="revision", payload={}, limits=Limits(requests=1))
    exhausted = execute(Runtime(revision_provider(), short), {})
    assert exhausted["request_count"] == 1
    assert exhausted["result"]["execution_error"] == "request_budget_exhausted"
    runtime = Runtime(Scripted([]), spec)
    runtime.started -= 301
    assert execute(runtime, {})["result"]["execution_error"] == "time_budget_exhausted"


def test_invalid_json_and_protected_core():
    spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
    receipt = execute(Runtime(Scripted([{"grant_authority": True}]), spec), {})
    assert receipt["result"]["execution_error"] == "invalid_model_json"
    with pytest.raises(ValueError):
        parse_record('{"core":"overwrite","instructions":"test"}', PromptVersion)


def test_store_idempotence_tamper_and_recovery(tmp_path):
    store = Store(tmp_path)
    spec = json_object(RunSpec(lab="ledger", payload=json_object(ledger_example())))
    run_id = store.enqueue("request-1", spec, {})
    assert store.enqueue("request-1", spec, {}) == run_id
    with pytest.raises(ValueError, match="conflict"):
        store.enqueue("request-1", {**spec, "lab": "graph"}, {})
    with pytest.raises(ValueError, match="active"):
        store.enqueue("request-2", spec, {})
    assert store.claim(run_id, 123)
    assert not store.claim(run_id, 123)
    store.cancel(run_id)
    assert store.cancelled(run_id)
    with store.connection() as db:
        db.execute("UPDATE runs SET created=? WHERE id=?", (time.time() - 1000, run_id))
    assert store.recover() == 1
    key = store.artifact({"test": "original"})
    (tmp_path / "artifacts" / (key + ".json")).write_text('{"test":"altered"}')
    with pytest.raises(ValueError, match="integrity"):
        store.read(key)
    with pytest.raises(ValueError):
        store.read("../escape")


def test_human_admission(tmp_path):
    store = Store(tmp_path)
    spec = RunSpec(lab="revision", payload={})
    receipt = execute(Runtime(revision_provider(), spec), {})
    run_id = store.enqueue("a", json_object(spec), {})
    store.claim(run_id, 123)
    store.finish(run_id, "completed", receipt)
    assert store.active_prompt() is None
    with pytest.raises(ValueError):
        store.admit(run_id, "viewer")
    key = store.admit(run_id, "operator")
    assert key == digest(receipt["result"]["child"])
    assert store.active_prompt() == receipt["result"]["child"]


def test_secrets_not_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-secret-value")
    store = Store(tmp_path)
    key = store.artifact({"reply": "private-secret-value"})
    assert "private-secret-value" not in canonical(store.read(key))
    with pytest.raises(ValueError, match="secret_in_input"):
        store.enqueue("a", {"input": "private-secret-value"}, {})


def test_unaccepted_premise_is_not_evidence():
    proposal = {
        "interpretation": "Assuming both reserves nonnegative, the target holds.",
        "verdict": "supported",
        "evidence_requests": [],
        "repairs": [],
    }
    spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
    receipt = execute(Runtime(Scripted([proposal]), spec), {})
    assert receipt["result"]["evaluation"]["verdict"] == "underdetermined"
    assert len(receipt["result"]["evaluation"]["accepted"]) == 1
    assert receipt["result"]["evaluation"]["obligations"][0]["state"] == "open"
    assert receipt["result"]["proposal"]["interpretation"] == proposal["interpretation"]


@pytest.mark.parametrize("error", [TimeoutError, RuntimeError])
def test_checker_failure(error, monkeypatch):
    def broken(_):
        raise error("not a mathematical refutation")

    monkeypatch.setattr("anomalon_workbench.ledger.evaluate", broken)
    receipt = execute(
        Runtime(Scripted([]), RunSpec(lab="ledger", payload=json_object(ledger_example()))), {}
    )
    assert receipt["status"] == "failed"
    assert receipt["result"]["host_evaluation"] == "not_evaluated"
    assert receipt["request_count"] == 0
