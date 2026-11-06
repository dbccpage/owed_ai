"""Tests for the tuner loop: separation rules, receipts, memory, demo and mutations."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from anomalon_workbench import tuner, tuner_demo
from anomalon_workbench.tuner import (
    Authorization,
    Candidate,
    Loop,
    Policy,
    PolicyAuthorizer,
    Receipt,
    ReceiptChainBroken,
    ReceiptLog,
    RoleConflict,
    SelfAuthorization,
    Verdict,
    authorize,
    learn,
    replay,
)


class FixedProposer:
    name = "fixed-proposer"

    def __init__(self, candidates: Sequence[Candidate]) -> None:
        self.candidates = list(candidates)

    def propose(self, context: Mapping[str, Any]) -> Sequence[Candidate]:
        return self.candidates


class TableEvaluator:
    name = "table-evaluator"

    def __init__(self, table: Mapping[str, tuple[str, float]]) -> None:
        self.table = table

    def evaluate(self, candidate: Candidate, history: Any) -> Verdict:
        status, improvement = self.table[str(candidate.payload["name"])]
        return Verdict(status, self.name, f"table says {status}", {"improvement": improvement})  # type: ignore[arg-type]


class RubberStamp:
    """An authorizer that approves everything; used to show the loop still refuses."""

    def __init__(self, name: str) -> None:
        self.name = name

    def authorize(self, candidate: Candidate, verdict: Verdict, policy: Policy) -> Authorization:
        return Authorization("approved", self.name, "stamped", policy.policy_id)


def cand(name: str, kind: str = "tweak") -> Candidate:
    return Candidate(kind, {"name": name}, "fixed-proposer")


POLICY = Policy("test/auto", auto_approve_kinds=frozenset({"tweak"}), min_improvement=0.0)


def test_receipt_chain_detects_corruption() -> None:
    log = ReceiptLog()
    log.append("proposed", "c1", {"a": 1})
    log.append("evaluated", "c1", {"b": 2})
    log.append("authorized", "c1", {"c": 3})
    assert log.verify() == -1
    receipts = log.to_json()
    receipts[1]["body"]["b"] = 99  # tamper with content, keep the hash
    assert ReceiptLog.from_json(receipts).verify() == 1
    receipts = log.to_json()
    receipts[2]["hash"] = "f" * 64  # corrupt a hash
    assert ReceiptLog.from_json(receipts).verify() == 2
    receipts = log.to_json()
    del receipts[1]  # drop a link: the next receipt's prev_hash no longer matches
    assert ReceiptLog.from_json(receipts).verify() == 1
    assert ReceiptLog.loads(log.dumps()).verify() == -1


def test_loop_refuses_broken_chain() -> None:
    log = ReceiptLog()
    log.append("proposed", "c1", {})
    broken = ReceiptLog([Receipt(0, "proposed", "c1", {}, tuner.GENESIS_HASH, "0" * 64)])
    loop = Loop(FixedProposer([]), TableEvaluator({}), PolicyAuthorizer(), POLICY, log=broken)
    with pytest.raises(ReceiptChainBroken):
        loop.run_once({}, None)


def test_role_conflict_is_refused() -> None:
    both = RubberStamp("fixed-proposer")  # same name as the proposer
    with pytest.raises(RoleConflict):
        Loop(FixedProposer([]), TableEvaluator({}), both, POLICY)
    evaluator = TableEvaluator({})
    with pytest.raises(RoleConflict):
        Loop(FixedProposer([]), evaluator, evaluator, POLICY)  # type: ignore[arg-type]


def test_self_authorization_is_refused() -> None:
    candidate = cand("x")
    verdict = Verdict("supported", "table-evaluator", "ok", {"improvement": 1.0})
    with pytest.raises(SelfAuthorization):
        authorize(RubberStamp("fixed-proposer"), candidate, verdict, POLICY)

    class Forwarder:
        name = "forwarder"

        def authorize(self, c: Candidate, v: Verdict, p: Policy) -> Authorization:
            return Authorization("approved", c.origin, "forwarded to the proposer", p.policy_id)

    with pytest.raises(SelfAuthorization):
        authorize(Forwarder(), candidate, verdict, POLICY)


def test_approval_requires_supported_verdict() -> None:
    candidate = cand("x")
    for status in ("refuted", "underdetermined"):
        verdict = Verdict(status, "table-evaluator", "no", {"improvement": 1.0})  # type: ignore[arg-type]
        auth = authorize(RubberStamp("stamp"), candidate, verdict, POLICY)
        assert auth.status == "denied"
        assert "not supported" in auth.reason


def test_policy_authorizer_rules() -> None:
    policy = Policy("p", auto_approve_kinds=frozenset({"a"}), human_review_kinds=frozenset({"h"}), min_improvement=0.5)
    pa = PolicyAuthorizer()
    good = Verdict("supported", "e", "ok", {"improvement": 0.9})
    assert pa.authorize(Candidate("a", {}, "p1"), good, policy).status == "approved"
    assert pa.authorize(Candidate("h", {}, "p1"), good, policy).status == "needs_human"
    assert pa.authorize(Candidate("z", {}, "p1"), good, policy).status == "needs_human"
    weak = Verdict("supported", "e", "ok", {"improvement": 0.1})
    assert pa.authorize(Candidate("a", {}, "p1"), weak, policy).status == "denied"
    missing = Verdict("supported", "e", "ok", {})
    assert pa.authorize(Candidate("a", {}, "p1"), missing, policy).status == "needs_human"
    assert pa.authorize(Candidate("a", {}, "p1"), Verdict("refuted", "e", "no"), policy).status == "denied"
    assert pa.authorize(Candidate("a", {}, "p1"), Verdict("underdetermined", "e", "?"), policy).status == "needs_human"


def test_loop_records_every_step_and_skips_known_mistakes() -> None:
    table = {"good": ("supported", 0.3), "bad": ("refuted", -0.2), "meh": ("underdetermined", 0.0)}
    proposer = FixedProposer([cand("good"), cand("bad"), cand("meh")])
    loop = Loop(proposer, TableEvaluator(table), PolicyAuthorizer(), POLICY)
    applied: list[str] = []

    def apply(c: Candidate) -> Mapping[str, Any]:
        applied.append(str(c.payload["name"]))
        return {"ok": True}

    first = loop.run_once({}, None, apply=apply, run_label="r1")
    assert (first.proposed, first.supported, first.refuted, first.underdetermined) == (3, 1, 1, 1)
    assert (first.approved, first.denied, first.needs_human, first.applied) == (1, 1, 1, 1)
    assert applied == ["good"]
    assert first.proposal_error_rate == pytest.approx(1 / 3)
    steps = [r.step for r in loop.log]
    assert steps == [
        "proposed", "evaluated", "authorized", "applied",
        "proposed", "evaluated", "learned", "authorized",
        "proposed", "evaluated", "authorized",
    ]
    assert loop.log.verify() == -1

    second = loop.run_once({}, None, apply=apply, run_label="r2")
    assert second.skipped_known_mistakes == 1
    assert second.refuted == 0
    assert [r.step for r in loop.log][11] in ("proposed", "skipped_known_mistake")
    assert any(r.step == "skipped_known_mistake" and r.candidate_id == cand("bad").candidate_id for r in loop.log)

    state = replay(loop.log)
    assert state["applied"] == [cand("good").candidate_id] * 2
    assert [m["candidate_id"] for m in state["mistakes"]] == [cand("bad").candidate_id]
    assert state["pending_human"] == [cand("meh").candidate_id] * 2
    assert len(first.pending_human) == 1

    # memory rebuilt from receipts alone matches the live memory
    rebuilt = learn(ReceiptLog.loads(loop.log.dumps()))
    assert [m.candidate_id for m in rebuilt.mistakes] == [m.candidate_id for m in loop.memory.mistakes]


def test_apply_failure_is_a_receipt_not_a_crash() -> None:
    loop = Loop(FixedProposer([cand("good")]), TableEvaluator({"good": ("supported", 1.0)}), PolicyAuthorizer(), POLICY)

    def apply(c: Candidate) -> Mapping[str, Any]:
        raise RuntimeError("store unavailable")

    summary = loop.run_once({}, None, apply=apply)
    assert summary.apply_failed == 1 and summary.applied == 0
    assert loop.log.receipts[-1].step == "apply_failed"
    assert "store unavailable" in str(loop.log.receipts[-1].body["error"])


def test_per_run_cap_defers_extra_changes() -> None:
    table = {"a": ("supported", 1.0), "b": ("supported", 1.0)}
    policy = Policy("cap", auto_approve_kinds=frozenset({"tweak"}), max_applied_per_run=1)
    loop = Loop(FixedProposer([cand("a"), cand("b")]), TableEvaluator(table), PolicyAuthorizer(), policy)
    summary = loop.run_once({}, None, apply=lambda c: {})
    assert (summary.applied, summary.deferred) == (1, 1)
    assert loop.log.receipts[-1].step == "deferred"


def test_demo_error_rates_fall_and_memory_stops_repeats() -> None:
    with_memory = tuner_demo.run_demo(seed=7, with_memory=True)
    no_memory = tuner_demo.run_demo(seed=7, with_memory=False)
    assert with_memory.task_error[0] == 1.0
    assert with_memory.task_error[-1] < 0.4
    assert with_memory.task_error[-1] == no_memory.task_error[-1]
    assert with_memory.log.verify() == -1
    # once a swap set is refuted, memory skips it on every later run; without memory it is re-refuted
    assert with_memory.proposal_error[-1] == 0.0 and sum(with_memory.skipped) > 0
    assert no_memory.proposal_error[-1] == 1.0 and sum(no_memory.skipped) == 0
    svg = tuner_demo.render_chart([with_memory, no_memory])
    assert svg.startswith("<svg") and "Proposal error" in svg
    json.dumps(with_memory.to_json())


def test_demo_is_deterministic() -> None:
    a = tuner_demo.run_demo(seed=3)
    b = tuner_demo.run_demo(seed=3)
    assert a.log.head == b.log.head and a.task_error == b.task_error


# --- mutation protocol: each fault must be caught by a check in this file or the engine ---


def test_mutation_corrupted_receipt_hash_is_caught() -> None:
    loop = Loop(FixedProposer([cand("good")]), TableEvaluator({"good": ("supported", 1.0)}), PolicyAuthorizer(), POLICY)
    loop.run_once({}, None)
    receipts = loop.log.to_json()
    receipts[0]["hash"] = receipts[0]["hash"][::-1]
    mutated = ReceiptLog.from_json(receipts)
    assert mutated.verify() == 0
    with pytest.raises(ReceiptChainBroken):
        replay(mutated)


def test_mutation_memory_removed_repeats_the_mistake() -> None:
    table = {"bad": ("refuted", -1.0)}
    loop = Loop(FixedProposer([cand("bad")]), TableEvaluator(table), PolicyAuthorizer(), POLICY, memory=tuner_demo.NullMemory())
    loop.run_once({}, None)
    second = loop.run_once({}, None)
    assert second.refuted == 1 and second.skipped_known_mistakes == 0  # the fault is visible
    intact = Loop(FixedProposer([cand("bad")]), TableEvaluator(table), PolicyAuthorizer(), POLICY)
    intact.run_once({}, None)
    assert intact.run_once({}, None).skipped_known_mistakes == 1  # the fix restores the skip


def test_mutation_evaluator_that_never_refutes_is_caught_by_receipt_audit() -> None:
    """Mutate the evaluator to call everything supported. The authorizer then approves bad
    swaps. The receipt audit (an independent recount from the recorded trace) catches it."""

    class AlwaysSupported:
        name = "always-supported"

        def evaluate(self, candidate: Candidate, history: Any) -> Verdict:
            state: tuner_demo.CacheState = history
            return Verdict("supported", self.name, "mutated", {"improvement": 1.0, "pinned_before": sorted(state.pinned_at_run_start)})

    trace = tuner_demo.zipf_trace(7, runs=8)
    state = tuner_demo.CacheState()
    policy = Policy("m", auto_approve_kinds=frozenset({"pin", "swap"}), max_applied_per_run=1)
    loop = Loop(tuner_demo.ToggleProposer(), AlwaysSupported(), PolicyAuthorizer(), policy)
    for index, segment in enumerate(trace):
        state.pinned_at_run_start = state.pinned

        def apply(c: Candidate) -> Mapping[str, Any]:
            state.pinned = tuner_demo.apply_candidate(state.pinned, c)
            return state.to_json()

        loop.run_once(state.context(), state, apply=apply, run_label=f"run-{index}")
        state.last_segment = list(segment)
    mismatches = tuner_demo.verify_receipts(loop.log, trace)
    assert mismatches, "the audit must flag the lying evaluator"
    assert all(r.step != "learned" for r in loop.log)  # nothing was ever refuted: the tell-tale
    honest = tuner_demo.run_demo(seed=7, runs=8)
    assert tuner_demo.verify_receipts(honest.log, tuner_demo.zipf_trace(7, runs=8)) == []
