"""Exact graph reconstruction and independently verifiable obstruction cycles."""

import re
from fractions import Fraction

from .domain import (
    Certificate,
    CycleCertificate,
    CycleStep,
    GraphEvaluation,
    GraphInput,
    PotentialCertificate,
    Repair,
    Verdict,
)


def rational(text: str, digits: int = 30) -> Fraction:
    if not re.fullmatch(rf"-?\d{{1,{digits}}}(?:/\d{{1,{digits}}})?", text):
        raise ValueError("expected_bounded_integer_or_fraction")
    return Fraction(text)


def validate(graph: GraphInput) -> None:
    if len(set(graph.vertices)) != len(graph.vertices) or any(not v for v in graph.vertices):
        raise ValueError("duplicate_or_empty_vertex")
    if len({e.id for e in graph.edges}) != len(graph.edges):
        raise ValueError("duplicate_edge_id")
    for edge in graph.edges:
        if not edge.id or edge.source not in graph.vertices or edge.target not in graph.vertices:
            raise ValueError("unknown_endpoint_or_empty_id")
        value = rational(edge.difference)
        if len(str(value.numerator)) > 30 or len(str(value.denominator)) > 30:
            raise ValueError("rational_out_of_bounds")


def evaluate(graph: GraphInput) -> GraphEvaluation:
    try:
        validate(graph)
    except (ValueError, ZeroDivisionError):
        return GraphEvaluation(
            verdict=Verdict.NOT_EVALUATED,
            certificate=None,
            reason="Malformed or out-of-bounds graph",
        )
    values: dict[str, Fraction] = {}
    paths: dict[str, tuple[CycleStep, ...]] = {}
    for root in graph.vertices:
        if root in values:
            continue
        values[root], paths[root] = Fraction(0), ()
        queue = [root]
        while queue:
            u = queue.pop(0)
            for edge in graph.edges:
                if edge.source == u:
                    v, direction = edge.target, 1
                elif edge.target == u:
                    v, direction = edge.source, -1
                else:
                    continue
                step = CycleStep(edge_id=edge.id, direction=1 if direction == 1 else -1)
                expected = values[u] + direction * Fraction(edge.difference)
                if v not in values:
                    values[v] = expected
                    paths[v] = (*paths[u], step)
                    queue.append(v)
                elif values[v] != expected:
                    reverse = tuple(
                        CycleStep(edge_id=s.edge_id, direction=-1 if s.direction == 1 else 1)
                        for s in reversed(paths[v])
                    )
                    return GraphEvaluation(
                        verdict=Verdict.REFUTED,
                        certificate=CycleCertificate(
                            steps=(*paths[u], step, *reverse), residual=str(expected - values[v])
                        ),
                        reason="A closed walk has nonzero residual; no global potential exists",
                    )
    return GraphEvaluation(
        verdict=Verdict.SUPPORTED,
        certificate=PotentialCertificate(values={v: str(q) for v, q in values.items()}),
        reason="Every edge agrees with the reconstructed potentials; each component is gauged independently",
    )


def verify(graph: GraphInput, certificate: Certificate) -> bool:
    """Check only certificate equations; does not call the reconstruction algorithm."""
    try:
        validate(graph)
        if isinstance(certificate, PotentialCertificate):
            if set(certificate.values) != set(graph.vertices):
                return False
            return all(
                rational(certificate.values[e.target], 512)
                - rational(certificate.values[e.source], 512)
                == Fraction(e.difference)
                for e in graph.edges
            )
        edges = {e.id: e for e in graph.edges}
        endpoints: list[tuple[str, str]] = []
        total = Fraction(0)
        if not certificate.steps or len(certificate.steps) > 32:
            return False
        for step in certificate.steps:
            edge = edges[step.edge_id]
            endpoints.append(
                (edge.source, edge.target) if step.direction == 1 else (edge.target, edge.source)
            )
            total += step.direction * Fraction(edge.difference)
        return (
            total != 0
            and total == rational(certificate.residual, 512)
            and all(
                endpoints[i][1] == endpoints[(i + 1) % len(endpoints)][0]
                for i in range(len(endpoints))
            )
        )
    except (ValueError, ZeroDivisionError, KeyError):
        return False


def repair(graph: GraphInput, changes: tuple[Repair, ...]) -> GraphInput:
    by_id = {r.edge_id: r.difference for r in changes}
    editable = {e.id for e in graph.edges if e.editable}
    if len(by_id) != len(changes) or not set(by_id) <= editable:
        raise ValueError("repair_changes_protected_or_unknown_edges")
    child = GraphInput(
        vertices=graph.vertices,
        edges=tuple(
            e.model_copy(update={"difference": by_id[e.id]}) if e.id in by_id else e
            for e in graph.edges
        ),
    )
    validate(child)
    return child
