"""Parameterized SQLite execution with content-bound simulated admission."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal

from .domain import Record, Verdict, digest
from .migration import Observation, Plan, Scenario, evaluate, valid_plan


class Admission(Record):
    scenario: str
    candidate: str
    evidence: str
    policy: Literal["synthetic-migration/1"] = "synthetic-migration/1"
    actor: Literal["simulated_operator"] = "simulated_operator"


class Execution(Record):
    rows: tuple[tuple[str, int], ...]
    committed: bool
    total_preserved: bool
    row_count_preserved: bool
    execution_conforms: bool
    ownership_preserved: bool | None


def admit(scenario: Scenario, plan: Plan, observations: tuple[Observation, ...]) -> Admission:
    if evaluate(scenario, plan, observations).ownership != Verdict.SUPPORTED:
        raise ValueError("ownership_not_established")
    return Admission(scenario=digest(scenario), candidate=digest(plan),
                     evidence=digest([o.model_dump(mode="json") for o in observations]))


def execute(path: Path, scenario: Scenario, plan: Plan,
            observations: tuple[Observation, ...] = (), admission: Admission | None = None,
            *, preview: bool = False, interrupt_after: int | None = None) -> Execution:
    if not valid_plan(scenario, plan):
        raise ValueError("invalid_mapping")
    if not preview and (admission is None or admission != admit(scenario, plan, observations)):
        raise ValueError("exact_admission_required")
    balances = {a.id: a.cents for a in scenario.accounts}
    with closing(sqlite3.connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            # Fresh destination only. Rerun is rejected without duplicating balances.
            db.execute("CREATE TABLE balances (destination TEXT PRIMARY KEY, cents INTEGER NOT NULL)")
            for index, link in enumerate(plan.links):
                db.execute("INSERT INTO balances VALUES (?,?)", (link.destination, balances[link.source]))
                if interrupt_after == index:
                    raise RuntimeError("injected_interruption")
            db.commit()
        except BaseException:
            db.rollback()
            raise
    # Separate read connection observes actual committed rows, never intended output alone.
    with closing(sqlite3.connect(path)) as observer:
        rows = tuple((str(d), int(c)) for d, c in observer.execute(
            "SELECT destination,cents FROM balances ORDER BY destination"))
    expected = {p.destination: balances[p.source] for p in plan.links}
    current = [o for o in observations if o.scope == scenario.scope and o.status == "observed"]
    mapping = {p.source: p.destination for o in current for p in o.links}
    ownership = None
    if evaluate(scenario, plan, observations).ownership == Verdict.SUPPORTED:
        remaining_sources = {a.id for a in scenario.accounts} - set(mapping)
        remaining_destinations = set(scenario.destinations) - set(mapping.values())
        if len(remaining_sources) == len(remaining_destinations) == 1:
            mapping[next(iter(remaining_sources))] = next(iter(remaining_destinations))
        ownership = all(dict(rows).get(mapping[a.id]) == a.cents for a in scenario.accounts)
    return Execution(rows=rows, committed=True,
        total_preserved=sum(c for _, c in rows) == sum(balances.values()),
        row_count_preserved=len(rows) == len(balances), execution_conforms=dict(rows) == expected,
        ownership_preserved=ownership)
