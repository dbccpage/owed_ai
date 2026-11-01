"""Bounded migration contracts, evidence evaluation and independent certificates.

The evaluator has no authority access. Every compatible mapping is enumerated
only within the declared 2–6 account model (at most 720 permutations).
"""

from __future__ import annotations

from itertools import permutations
from typing import Literal, Protocol

from pydantic import Field, model_validator

from .domain import Record, Verdict, digest


class Account(Record):
    id: str = Field(min_length=1, max_length=40)
    cents: int = Field(ge=-1_000_000_000, le=1_000_000_000)


class Scope(Record):
    snapshot: str = Field(min_length=1, max_length=80)
    roster: str = Field(min_length=1, max_length=80)
    crosswalk: str = Field(min_length=1, max_length=80)
    unit: Literal["USD-cent"] = "USD-cent"


class Scenario(Record):
    seed: int = Field(ge=0, le=2**32 - 1)
    scope: Scope
    accounts: tuple[Account, ...] = Field(min_length=2, max_length=6)
    destinations: tuple[str, ...] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def unique(self) -> Scenario:
        sources = {a.id for a in self.accounts}
        if (len(sources) != len(self.accounts)
            or len(set(self.destinations)) != len(self.destinations)
            or len(self.accounts) != len(self.destinations)
            or any(not d or len(d) > 40 for d in self.destinations)
            or sources & set(self.destinations)):
            raise ValueError("distinct_disjoint_equal_size_rosters_required")
        return self


class Link(Record):
    source: str = Field(min_length=1, max_length=40)
    destination: str = Field(min_length=1, max_length=40)


class Plan(Record):
    version: int = Field(ge=1, le=1000)
    origin: Literal["fixture", "evidence_repair", "model_proposal"] = "fixture"
    links: tuple[Link, ...] = Field(max_length=6)


class Observation(Record):
    scope: Scope
    authority: Literal["synthetic-source/v1"] = "synthetic-source/v1"
    links: tuple[Link, ...] = Field(max_length=6)
    status: Literal["observed", "unavailable"] = "observed"


class Witness(Record):
    first: Plan
    second: Plan
    source: str


class Obligation(Record):
    claim: Literal["ownership"] = "ownership"
    dependencies: tuple[str, ...]
    state: Literal["open", "discharged", "failed"]
    resolution: str = "Obtain consistent current correspondence covering every source"
    explanation: str


class Evaluation(Record):
    ownership: Verdict
    evidence_status: tuple[Literal["accepted", "stale", "unavailable"], ...]
    compatible_count: int
    witness: Witness | None = None
    mismatch: Link | None = None
    conflicts: tuple[str, ...] = ()
    obligation: Obligation


def valid_plan(scenario: Scenario, plan: Plan) -> bool:
    return (len(plan.links) == len(scenario.accounts)
            and {p.source for p in plan.links} == {a.id for a in scenario.accounts}
            and {p.destination for p in plan.links} == set(scenario.destinations))


def compatible(scenario: Scenario, observations: tuple[Observation, ...]) -> tuple[Plan, ...]:
    accepted = [o for o in observations if o.scope == scenario.scope and o.status == "observed"]
    requirements = [p for o in accepted for p in o.links]
    sources = sorted(a.id for a in scenario.accounts)
    return tuple(
        Plan(version=1, links=tuple(Link(source=s, destination=d) for s, d in zip(sources, ds)))
        for ds in permutations(sorted(scenario.destinations))
        if all(p.source in sources and ds[sources.index(p.source)] == p.destination
               for p in requirements)
    )


def evaluate(scenario: Scenario, plan: Plan, observations: tuple[Observation, ...]) -> Evaluation:
    statuses: tuple[Literal["accepted", "stale", "unavailable"], ...] = tuple(
        "unavailable" if o.status == "unavailable" else "stale" if o.scope != scenario.scope
        else "accepted" for o in observations
    )
    states = compatible(scenario, observations)
    dependencies = tuple(digest(o) for o in observations)
    target = {p.source: p.destination for p in plan.links}
    agrees = [p for p in states if {q.source: q.destination for q in p.links} == target]
    verdict = (Verdict.NOT_EVALUATED if not valid_plan(scenario, plan)
               else Verdict.INCONSISTENT if not states
               else Verdict.REFUTED if not agrees
               else Verdict.SUPPORTED if len(states) == 1
               else Verdict.UNDERDETERMINED)
    witness = None
    if len(states) > 1:
        first, second = states[:2]
        source = next(a.source for a, b in zip(first.links, second.links)
                      if a.destination != b.destination)
        witness = Witness(first=first, second=second, source=source)
    mismatch = None
    if verdict == Verdict.REFUTED:
        # Only report a single mismatch when evidence fixes that source's destination.
        for source, destination in target.items():
            possible = {p.destination for state in states for p in state.links if p.source == source}
            if len(possible) == 1 and destination not in possible:
                mismatch = Link(source=source, destination=next(iter(possible)))
                break
    conflicts = tuple(digest(o) for o, status in zip(observations, statuses)
                      if status == "accepted") if not states else ()
    return Evaluation(
        ownership=verdict, evidence_status=statuses, compatible_count=len(states),
        witness=witness, mismatch=mismatch, conflicts=conflicts,
        obligation=Obligation(dependencies=dependencies,
            state="discharged" if verdict == Verdict.SUPPORTED else "open"
            if verdict == Verdict.UNDERDETERMINED else "failed",
            explanation=f"{len(states)} mappings compatible with current accepted observations"),
    )


def verify_witness(scenario: Scenario, observations: tuple[Observation, ...], witness: Witness) -> bool:
    """Direct certificate check: no call to compatible(), evaluate() or constructor."""
    tables = []
    for candidate in (witness.first, witness.second):
        table = {p.source: p.destination for p in candidate.links}
        if (len(table) != len(candidate.links) or set(table) != {a.id for a in scenario.accounts}
            or len(set(table.values())) != len(scenario.destinations)
            or set(table.values()) != set(scenario.destinations)):
            return False
        for observation in observations:
            if observation.scope == scenario.scope and observation.status == "observed":
                if any(table.get(p.source) != p.destination for p in observation.links):
                    return False
        tables.append(table)
    return (witness.source in tables[0]
            and tables[0][witness.source] != tables[1][witness.source])


class EvidenceAction(Record):
    kind: Literal["repeat_total", "source", "full_crosswalk"]
    source: str = ""
    cost: int = Field(ge=0)


class EvidencePort(Protocol):
    def obtain(self, scope: Scope, action: EvidenceAction) -> Observation: ...


def select_action(scenario: Scenario, observations: tuple[Observation, ...]) -> EvidenceAction | None:
    """Lowest cost informative action in this finite menu, deterministic ties.

    This does not claim minimum total cost of a complete adaptive strategy.
    """
    states = compatible(scenario, observations)
    if len(states) < 2:
        return None
    actions = [EvidenceAction(kind="repeat_total", cost=0),
               EvidenceAction(kind="full_crosswalk", cost=max(1, len(scenario.accounts) - 1))]
    actions += [EvidenceAction(kind="source", source=a.id, cost=2) for a in scenario.accounts]
    def informative(action: EvidenceAction) -> bool:
        if action.kind == "repeat_total":
            return False  # all states have the same balances and total
        if action.kind == "full_crosswalk":
            return True
        return len({p.destination for state in states for p in state.links
                    if p.source == action.source}) > 1
    return min((a for a in actions if informative(a)),
               key=lambda a: (a.cost, a.kind, a.source))
