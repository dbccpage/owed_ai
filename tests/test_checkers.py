import json
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as s
from pydantic import ValidationError

from anomalon_workbench import graphs, ledger
from anomalon_workbench.domain import (
    CycleCertificate,
    Edge,
    GraphInput,
    LedgerInput,
    Observation,
    PotentialCertificate,
    Repair,
    Verdict,
)
from anomalon_workbench.examples import graph_example, ledger_example
from anomalon_workbench.service import parse_record


@pytest.mark.parametrize(
    "b,verdict,allowed",
    [
        (None, Verdict.UNDERDETERMINED, False),
        (20, Verdict.SUPPORTED, True),
        (-20, Verdict.REFUTED, False),
    ],
)
def test_ledger_branches(b, verdict, allowed):
    data = ledger_example(b, "operator")
    result = ledger.evaluate(data)
    assert result.verdict == verdict
    assert result.authorization.allowed == allowed
    assert ledger.verify(data, result)


def test_frozen_fixtures():
    path = Path(__file__).parents[1] / "fixtures" / "ledger.json"
    for case in json.loads(path.read_text()):
        data = parse_record(json.dumps(case["input"]), LedgerInput)
        result = ledger.evaluate(data)
        assert result.verdict.value == case["verdict"], case["id"]
        assert result.authorization.allowed == case["authorized"], case["id"]
        assert ledger.verify(data, result), case["id"]


def test_counts_scope_and_wrong_actor():
    initial = ledger.evaluate(ledger_example())
    assert (initial.compatible, initial.satisfying, initial.falsifying) == (121, 101, 20)
    assert not ledger.evaluate(ledger_example(20)).authorization.allowed
    stale = LedgerInput(observations=(Observation(field="b", value=20, snapshot="old"),))
    assert ledger.evaluate(stale).verdict == Verdict.UNDERDETERMINED
    wrong_unit = LedgerInput(observations=(Observation(field="b", value=20, units="cents"),))
    assert ledger.evaluate(wrong_unit).verdict == Verdict.NOT_EVALUATED


@given(s.integers(min_value=-30, max_value=110))
def test_every_b(b):
    data = ledger_example(b)
    result = ledger.evaluate(data)
    expected = (
        Verdict.INCONSISTENT
        if b < -20 or b > 100
        else Verdict.SUPPORTED
        if b >= 0
        else Verdict.REFUTED
    )
    assert result.verdict == expected
    assert ledger.verify(data, result)


def test_contradiction_and_corrupted_witnesses():
    data = LedgerInput(
        observations=(Observation(field="b", value=20), Observation(field="b", value=-20))
    )
    assert ledger.evaluate(data).verdict == Verdict.INCONSISTENT
    original = ledger_example()
    result = ledger.evaluate(original)
    assert not ledger.verify(original, result.model_copy(update={"witnesses": ((999, 999),)}))
    assert not ledger.verify(original, result.model_copy(update={"satisfying": 121}))


def test_graph_cycle_and_pairwise_consistency():
    graph = graph_example()
    result = graphs.evaluate(graph)
    assert result.verdict == Verdict.REFUTED
    assert graphs.verify(graph, result.certificate)
    for omitted in range(3):
        pair = graph.model_copy(
            update={"edges": tuple(e for i, e in enumerate(graph.edges) if i != omitted)}
        )
        positive = graphs.evaluate(pair)
        assert positive.verdict == Verdict.SUPPORTED
        assert graphs.verify(pair, positive.certificate)
    assert not graphs.verify(graph, result.certificate.model_copy(update={"residual": "0"}))
    assert not graphs.verify(graph, CycleCertificate(steps=(), residual="1"))
    assert not graphs.verify(graph, PotentialCertificate(values={"A": "0", "B": "1", "C": "2"}))


def test_graph_repair_protection_and_disconnected():
    original = graph_example()
    repaired = graphs.repair(original, (Repair(edge_id="ac", difference="2"),))
    assert original.edges[-1].difference == "3"
    assert graphs.evaluate(repaired).verdict == Verdict.SUPPORTED
    with pytest.raises(ValueError):
        graphs.repair(original, (Repair(edge_id="ab", difference="2"),))
    disconnected = GraphInput(vertices=("A", "B", "C"), edges=(original.edges[0],))
    result = graphs.evaluate(disconnected)
    assert result.verdict == Verdict.SUPPORTED
    assert graphs.verify(disconnected, result.certificate)


@given(s.integers(-100, 100), s.integers(-100, 100), s.integers(1, 20))
def test_rational_reconstruction(x, y, denominator):
    graph = GraphInput(
        vertices=("a", "b", "c"),
        edges=(
            Edge(id="ab", source="a", target="b", difference=str(Fraction(x, denominator))),
            Edge(id="bc", source="b", target="c", difference=str(Fraction(y, denominator))),
            Edge(id="ac", source="a", target="c", difference=str(Fraction(x + y, denominator))),
        ),
    )
    result = graphs.evaluate(graph)
    assert result.verdict == Verdict.SUPPORTED
    assert graphs.verify(graph, result.certificate)


@pytest.mark.parametrize("difference", ["bad", "1/0", "9" * 40])
def test_malformed_graph(difference):
    graph = GraphInput(
        vertices=("a",), edges=(Edge(id="e", source="a", target="a", difference=difference),)
    )
    assert graphs.evaluate(graph).verdict == Verdict.NOT_EVALUATED


def test_self_loop_and_parallel_edges():
    loop = GraphInput(
        vertices=("a",), edges=(Edge(id="e", source="a", target="a", difference="1"),)
    )
    assert graphs.verify(loop, graphs.evaluate(loop).certificate)
    parallel = GraphInput(
        vertices=("a", "b"),
        edges=(
            Edge(id="e", source="a", target="b", difference="1"),
            Edge(id="f", source="a", target="b", difference="2"),
        ),
    )
    assert graphs.verify(parallel, graphs.evaluate(parallel).certificate)


def test_strict_boundary():
    with pytest.raises((ValueError, ValidationError)):
        parse_record('{"actor":"viewer","actor":"operator"}', LedgerInput)
    with pytest.raises(ValidationError):
        parse_record('{"grant_authority":true}', LedgerInput)


def test_reject_exponent_before_fraction_expansion():
    graph = GraphInput(
        vertices=("a",), edges=(Edge(id="e", source="a", target="a", difference="1e999999999"),)
    )
    assert graphs.evaluate(graph).verdict == Verdict.NOT_EVALUATED
