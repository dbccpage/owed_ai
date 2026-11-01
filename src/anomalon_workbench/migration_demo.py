"""Synthetic authority adapter and reproducible application service; no provider calls."""

from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field, JsonValue, model_validator

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
    response_matches_action,
    select_action,
    valid_plan,
    verify_witness,
)
from .migration_execution import Admission, Execution, admit, execute
from .migration_proof import proof_status

Mode = Literal["valid", "missing", "stale", "contradictory"]


class SyntheticAuthority:
    """Trusted only within this declared synthetic scenario. Never passed to evaluator."""

    def __init__(self, scenario: Scenario, mapping: Plan, mode: Mode = "valid"):
        self.scenario, self.mapping, self.mode = scenario, mapping, mode

    def obtain(self, scope: Scope, action: EvidenceAction) -> Observation:
        if scope != self.scenario.scope or action.kind == "repeat_total":
            raise ValueError("unsupported_or_uninformative_request")
        observed_scope = (
            scope.model_copy(update={"crosswalk": "old"}) if self.mode == "stale" else scope
        )
        links = tuple(
            p
            for p in self.mapping.links
            if action.kind == "full_crosswalk" or p.source == action.source
        )
        if self.mode == "contradictory":
            from .migration import Link

            first = links[0]
            other = next(d for d in self.scenario.destinations if d != first.destination)
            links = (first, Link(source=first.source, destination=other))
        return Observation(
            scope=observed_scope,
            links=() if self.mode == "missing" else links,
            status="unavailable" if self.mode == "missing" else "observed",
        )


def fixture(seed: int = 0, count: int = 3) -> tuple[Scenario, Plan, Plan]:
    """Return public data + fixture candidate + authority-only correspondence.

    Public rosters are shuffled independently. Crosswalk is supplied only to the
    authority adapter, never to witness construction or evidence selection.
    """
    rng = random.Random(seed)
    sources = [f"S-{seed:x}-{i}" for i in range(count)]
    destinations = [f"N-{seed:x}-{i}" for i in range(count)]
    amounts = (
        [70000, 20000, 10000]
        if seed == 0 and count == 3
        else [rng.randint(-100000, 100000) for _ in sources]
    )
    accounts = [Account(id=s, cents=c) for s, c in zip(sources, amounts)]
    shuffled = list(destinations)
    rng.shuffle(shuffled)
    from .migration import Link

    authority = Plan(
        version=1, links=tuple(Link(source=s, destination=d) for s, d in zip(sources, shuffled))
    )
    # Deliberately insufficient fixture, not a representative LLM performance claim.
    candidate = Plan(
        version=1,
        links=tuple(
            Link(source=s, destination=d) for s, d in zip(sources, shuffled[1:] + shuffled[:1])
        ),
    )
    rng.shuffle(accounts)
    rng.shuffle(destinations)
    return (
        Scenario(
            seed=seed,
            scope=Scope(snapshot=f"s-{seed}", roster=f"r-{seed}", crosswalk=f"c-{seed}"),
            accounts=tuple(accounts),
            destinations=tuple(destinations),
        ),
        candidate,
        authority,
    )


class Step(Record):
    action: EvidenceAction
    observation: Observation
    rationale: str = "Lowest-cost informative action in the evaluated menu; total query cannot distinguish mappings"


class Receipt(Record):
    schema_version: Literal["migration/1"] = "migration/1"
    checker: Literal["migration/1"] = "migration/1"
    application_build: str
    run_id: str
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
    formal_artifact: dict[str, JsonValue]

    @model_validator(mode="after")
    def binding(self) -> Receipt:
        if self.observations != self.initial_observations + tuple(
            s.observation for s in self.steps
        ):
            raise ValueError("unrecorded_evidence")
        return self


def run(
    scenario: Scenario,
    original: Plan,
    port: EvidencePort,
    initial_observations: tuple[Observation, ...] = (),
    *,
    prior: Receipt | None = None,
    acquire: bool = True,
    one_action: bool = False,
) -> Receipt:
    if prior is not None:
        if prior.scenario != scenario or prior.original != original:
            raise ValueError("prior_scope_mismatch")
        if not replay(export(prior)):
            raise ValueError("invalid_prior_receipt")
        initial_observations = prior.initial_observations
    initial = evaluate(scenario, original, initial_observations)
    if initial.witness and not verify_witness(scenario, initial_observations, initial.witness):
        raise ValueError("invalid_witness")
    observations = prior.observations if prior else initial_observations
    steps: list[Step] = list(prior.steps) if prior else []
    # The temporary directory is scoped to one invocation and cleaned on every exit.
    with tempfile.TemporaryDirectory(prefix="owed-migration-") as directory:
        preview = (
            prior.preview
            if prior
            else execute(Path(directory) / "preview.sqlite3", scenario, original, preview=True)
        )
        for _ in range(min(6, 8 - len(steps)) if acquire else 0):
            action = select_action(scenario, observations)
            if action is None:
                break
            try:
                observation = port.obtain(scenario.scope, action)
            except (OSError, TimeoutError):
                observation = Observation(
                    scope=scenario.scope,
                    links=(),
                    status="unavailable",
                    issue="Evidence adapter unavailable; no truth conclusion",
                )
            if not response_matches_action(action, observation):
                raise ValueError("evidence_response_contract")
            observations = (*observations, observation)
            steps.append(Step(action=action, observation=observation))
            if (
                one_action
                or observation.scope != scenario.scope
                or observation.status == "unavailable"
            ):
                break
        final = evaluate(scenario, original, observations)
        repaired = None
        admission = None
        execution = None
        if (
            acquire
            and final.ownership in (Verdict.REFUTED, Verdict.SUPPORTED)
            and final.compatible_count == 1
        ):
            from .migration import compatible

            justified = compatible(scenario, observations)[0]
            repaired = Plan(
                version=original.version + 1, origin="evidence_repair", links=justified.links
            )
            admission = admit(scenario, repaired, observations)
            execution = execute(
                Path(directory) / "repair.sqlite3", scenario, repaired, observations, admission
            )
    import hashlib

    source = Path(__file__).parent
    build = digest(
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob("*.py"))}
    )
    return Receipt(
        application_build=build,
        run_id=digest(
            {
                "scenario": digest(scenario),
                "candidate": digest(original),
                "evidence": [digest(o) for o in observations],
            }
        ),
        formal_artifact=proof_status(),
        scenario=scenario,
        original=original,
        preview=preview,
        initial=initial,
        initial_observations=initial_observations,
        steps=tuple(steps),
        observations=observations,
        final=final,
        repaired=repaired,
        admission=admission,
        execution=execution,
    )


def export(receipt: Receipt) -> str:
    return canonical({"sha256": digest(receipt), "receipt": receipt.model_dump(mode="json")})


def replay(raw: str) -> bool:
    """Bounded offline re-evaluation; never queries authority or calls execute()."""
    if len(raw.encode("utf-8")) > 100000:
        raise ValueError("bundle_too_large")
    from .service import unique_object

    try:
        bundle = json.loads(raw, object_pairs_hook=unique_object)
    except (RecursionError, TypeError) as exc:
        raise ValueError("invalid_bundle_structure") from exc
    if not isinstance(bundle, dict):
        raise ValueError("bundle_object_required")
    if set(bundle) != {"sha256", "receipt"} or digest(bundle["receipt"]) != bundle["sha256"]:
        return False
    r = Receipt.model_validate_json(canonical(bundle["receipt"]))
    if not valid_plan(r.scenario, r.original):
        return False
    expected_id = digest(
        {
            "scenario": digest(r.scenario),
            "candidate": digest(r.original),
            "evidence": [digest(o) for o in r.observations],
        }
    )
    if r.run_id != expected_id:
        return False
    if evaluate(r.scenario, r.original, r.initial_observations) != r.initial:
        return False
    if evaluate(r.scenario, r.original, r.observations) != r.final:
        return False
    if r.initial.witness and not verify_witness(
        r.scenario, r.initial_observations, r.initial.witness
    ):
        return False
    previous = r.initial_observations
    for step in r.steps:
        if step.action != select_action(r.scenario, previous):
            return False
        if not response_matches_action(step.action, step.observation):
            return False
        previous += (step.observation,)
    for plan, execution in ((r.original, r.preview), (r.repaired, r.execution)):
        if plan is None or execution is None:
            if plan is not None or execution is not None:
                return False
            continue
        # Direct observer reconstructs each destination balance from included source rows.
        expected = sorted(
            (p.destination, a.cents)
            for p in plan.links
            for a in r.scenario.accounts
            if a.id == p.source
        )
        total = sum(c for _, c in execution.rows) == sum(a.cents for a in r.scenario.accounts)
        count = len(execution.rows) == len(r.scenario.accounts)
        owned = True if plan == r.repaired else None
        if (
            list(execution.rows) != expected
            or not execution.execution_conforms
            or not execution.committed
            or execution.total_preserved != total
            or execution.row_count_preserved != count
            or execution.identity_coverage
            != (set(dict(execution.rows)) == set(r.scenario.destinations))
            or execution.ownership_preserved != owned
        ):
            return False
    if r.repaired is not None:
        if (
            not valid_plan(r.scenario, r.repaired)
            or r.repaired.origin != "evidence_repair"
            or r.repaired.version != r.original.version + 1
        ):
            return False
        if r.admission != admit(r.scenario, r.repaired, r.observations):
            return False
    elif r.admission is not None:
        return False
    elif r.steps and r.final.compatible_count == 1:
        return False  # acquisition reached a justified mapping: repair cannot be silently omitted
    return True


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Owed synthetic migration; no model API calls")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--count", type=int, choices=range(2, 7), default=3)
    parser.add_argument(
        "--mode", choices=("valid", "missing", "stale", "contradictory"), default="valid"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.replay:
        with args.replay.open(encoding="utf-8") as handle:
            raw = handle.read(100001)
        try:
            matched = replay(raw)
        except (ValueError, KeyError, TypeError, RecursionError):
            parser.error("Invalid, oversized or unsupported receipt; nothing executed")
        print(json.dumps({"offline_replay_matched": matched, "execution_authorized": False}))
        if not matched:
            raise SystemExit(1)
        return
    scenario, candidate, truth = fixture(args.seed, args.count)
    receipt = run(scenario, candidate, SyntheticAuthority(scenario, truth, args.mode))
    bundle = export(receipt)
    if args.output:
        args.output.write_text(bundle + "\n", encoding="utf-8")
    else:
        print(bundle)


if __name__ == "__main__":
    main()
