"""Public starter inputs; withheld labels are computed only in the evaluator."""

from .domain import Edge, GraphInput, LedgerInput, Observation, PromptVersion


def ledger_example(b: int | None = None, actor: str = "viewer") -> LedgerInput:
    observations = [Observation(field="total", value=100)]
    if b is not None:
        observations.append(Observation(field="b", value=b))
    return LedgerInput(
        observations=tuple(observations), actor="operator" if actor == "operator" else "viewer"
    )


def graph_example() -> GraphInput:
    return GraphInput(
        vertices=("A", "B", "C"),
        edges=(
            Edge(id="ab", source="A", target="B", difference="1"),
            Edge(id="bc", source="B", target="C", difference="1"),
            Edge(id="ac", source="A", target="C", difference="3", editable=True),
        ),
    )


def initial_prompt() -> PromptVersion:
    return PromptVersion(
        instructions="Evaluate the requested claim carefully. State what evidence is missing."
    )


def revision_cases() -> tuple[tuple[str, LedgerInput], ...]:
    contradictory = LedgerInput(
        observations=(
            Observation(field="total", value=100),
            Observation(field="b", value=20),
            Observation(field="b", value=-20),
        )
    )
    return (
        ("dev-total", ledger_example()),
        ("dev-positive", ledger_example(20)),
        ("heldout-negative", ledger_example(-20)),
        ("heldout-conflict", contradictory),
    )
