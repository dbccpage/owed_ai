"""Synthetic authority adapter and reproducible application service; no provider calls."""

from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .domain import Record, Verdict, canonical, digest
from .migration import (
    Account,
    Evaluation,
    EvidenceAction,
    EvidencePort,
    Observation,
    Plan,
    Scenario,
    Scope,
    evaluate,
    select_action,
    verify_witness,
)
from .migration_execution import Admission, Execution, admit, execute

Mode = Literal["valid", "missing", "stale", "contradictory"]


class SyntheticAuthority:
    """Trusted only within this declared synthetic scenario. Never passed to evaluator."""

    def __init__(self, scenario: Scenario, mapping: Plan, mode: Mode = "valid"):
        self.scenario, self.mapping, self.mode = scenario, mapping, mode

    def obtain(self, scope: Scope, action: EvidenceAction) -> Observation:
        if scope != self.scenario.scope or action.kind == "repeat_total":
            raise ValueError("unsupported_or_uninformative_request")
        observed_scope = scope.model_copy(update={"crosswalk": "old"}) if self.mode == "stale" else scope
        links = tuple(p for p in self.mapping.links
                      if action.kind == "full_crosswalk" or p.source == action.source)
        return Observation(scope=observed_scope, links=links,
                           status="unavailable" if self.mode == "missing" else "observed")


def fixture(seed: int = 0, count: int = 3) -> tuple[Scenario, Plan, Plan]:
    """Return public data + fixture candidate + authority-only correspondence.

    Public rosters are shuffled independently. Crosswalk is supplied only to the
    authority adapter, never to witness construction or evidence selection.
    """
    rng = random.Random(seed)
    sources = [f"S-{seed:x}-{i}" for i in range(count)]
    destinations = [f"N-{seed:x}-{i}" for i in range(count)]
    amounts = [70000, 20000, 10000] if seed == 0 and count == 3 else [
        rng.randint(-100000, 100000) for _ in sources]
    accounts = [Account(id=s, cents=c) for s, c in zip(sources, amounts)]
    shuffled = list(destinations)
    rng.shuffle(shuffled)
    from .migration import Link

    authority = Plan(version=1, links=tuple(Link(source=s, destination=d)
                                          for s, d in zip(sources, shuffled)))
    # Deliberately insufficient fixture, not a representative LLM performance claim.
    candidate = Plan(version=1, links=tuple(Link(source=s, destination=d)
                       for s, d in zip(sources, shuffled[1:] + shuffled[:1])))
    rng.shuffle(accounts)
    rng.shuffle(destinations)
    return Scenario(seed=seed, scope=Scope(snapshot=f"s-{seed}", roster=f"r-{seed}",
        crosswalk=f"c-{seed}"), accounts=tuple(accounts), destinations=tuple(destinations)), candidate, authority


class Step(Record):
    action: EvidenceAction
    observation: Observation
    rationale: str = "Lowest-cost informative action in the evaluated menu; total query cannot distinguish mappings"


class Receipt(Record):
    schema_version: Literal["migration/1"] = "migration/1"
    checker: Literal["migration/1"] = "migration/1"
    scenario: Scenario
    original: Plan
    preview: Execution
    initial: Evaluation
    initial_observations: tuple[Observation, ...] = Field(max_length=10)
    steps: tuple[Step, ...] = Field(max_length=8)
    observations: tuple[Observation, ...] = Field(max_length=10)
    final: Evaluation
    repaired: Plan | None
    admission: Admission | None
    execution: Execution | None
    formal_status: Literal["not_verified_for_this_build"] = "not_verified_for_this_build"

    @model_validator(mode="after")
    def binding(self) -> Receipt:
        if any(step.observation not in self.observations for step in self.steps):
            raise ValueError("unrecorded_evidence")
        return self


def run(scenario: Scenario, original: Plan, port: EvidencePort,
        initial_observations: tuple[Observation, ...] = ()) -> Receipt:
    initial = evaluate(scenario, original, initial_observations)
    if initial.witness and not verify_witness(scenario, initial_observations, initial.witness):
        raise ValueError("invalid_witness")
    observations = initial_observations
    steps: list[Step] = []
    # The temporary directory is scoped to one invocation and cleaned on every exit.
    with tempfile.TemporaryDirectory(prefix="owed-migration-") as directory:
        preview = execute(Path(directory) / "preview.sqlite3", scenario, original, preview=True)
        for _ in range(6):
            action = select_action(scenario, observations)
            if action is None:
                break
            observation = port.obtain(scenario.scope, action)
            observations = (*observations, observation)
            steps.append(Step(action=action, observation=observation))
            if observation.scope != scenario.scope or observation.status == "unavailable":
                break
        final = evaluate(scenario, original, observations)
        repaired = None
        admission = None
        execution = None
        if final.ownership in (Verdict.REFUTED, Verdict.SUPPORTED) and final.compatible_count == 1:
            from .migration import compatible

            justified = compatible(scenario, observations)[0]
            repaired = Plan(version=original.version + 1, origin="evidence_repair", links=justified.links)
            admission = admit(scenario, repaired, observations)
            execution = execute(Path(directory) / "repair.sqlite3", scenario, repaired, observations, admission)
    return Receipt(scenario=scenario, original=original, preview=preview, initial=initial,
        initial_observations=initial_observations, steps=tuple(steps), observations=observations, final=final, repaired=repaired,
        admission=admission, execution=execution)


def export(receipt: Receipt) -> str:
    return canonical({"sha256": digest(receipt), "receipt": receipt.model_dump(mode="json")})


def replay(raw: str) -> bool:
    """Bounded offline re-evaluation; never queries authority or calls execute()."""
    if len(raw.encode("utf-8")) > 100000:
        raise ValueError("bundle_too_large")
    from .service import unique_object

    bundle = json.loads(raw, object_pairs_hook=unique_object)
    if set(bundle) != {"sha256", "receipt"} or digest(bundle["receipt"]) != bundle["sha256"]:
        return False
    r = Receipt.model_validate_json(canonical(bundle["receipt"]))
    if evaluate(r.scenario, r.original, r.initial_observations) != r.initial:
        return False
    if evaluate(r.scenario, r.original, r.observations) != r.final:
        return False
    if r.initial.witness and not verify_witness(r.scenario, r.initial_observations, r.initial.witness):
        return False
    for plan, execution in ((r.original, r.preview), (r.repaired, r.execution)):
        if plan is None or execution is None:
            if plan is not None or execution is not None:
                return False
            continue
        # Direct observer reconstructs each destination balance from included source rows.
        expected = sorted((p.destination, a.cents) for p in plan.links
                          for a in r.scenario.accounts if a.id == p.source)
        if list(execution.rows) != expected or not execution.execution_conforms:
            return False
    if r.repaired is not None:
        if r.admission != admit(r.scenario, r.repaired, r.observations):
            return False
    return True
