import sqlite3

import pytest

from anomalon_workbench.domain import Verdict
from anomalon_workbench.migration import Observation, evaluate, verify_witness
from anomalon_workbench.migration_demo import SyntheticAuthority, export, fixture, replay, run
from anomalon_workbench.migration_execution import admit, execute


@pytest.mark.parametrize("seed", range(100))
def test_generated_repair_and_independent_observer(seed):
    scenario, original, truth = fixture(seed, 2 + seed % 5)
    receipt = run(scenario, original, SyntheticAuthority(scenario, truth))
    assert receipt.initial.ownership == Verdict.UNDERDETERMINED
    assert verify_witness(scenario, (), receipt.initial.witness)
    assert receipt.final.ownership == Verdict.REFUTED
    expected = {
        p.destination: a.cents for p in truth.links for a in scenario.accounts if a.id == p.source
    }
    assert dict(receipt.execution.rows) == expected
    assert receipt.execution.ownership_preserved
    assert replay(export(receipt))


def test_missing_stale_conflicting_and_correct():
    s, candidate, truth = fixture()
    for mode in ("missing", "stale"):
        r = run(s, candidate, SyntheticAuthority(s, truth, mode))
        assert r.final.ownership == Verdict.UNDERDETERMINED
        assert r.execution is None
        assert replay(export(r))
    conflicting = (
        Observation(scope=s.scope, links=truth.links),
        Observation(scope=s.scope, links=candidate.links),
    )
    result = evaluate(s, candidate, conflicting)
    assert result.ownership == Verdict.INCONSISTENT
    assert len(result.conflicts) == 2
    r = run(s, truth, SyntheticAuthority(s, truth))
    assert r.final.ownership == Verdict.SUPPORTED
    assert r.execution.ownership_preserved


def test_atomic_execution_and_exact_admission(tmp_path):
    s, candidate, truth = fixture()
    observations = (Observation(scope=s.scope, links=truth.links),)
    admission = admit(s, truth, observations)
    path = tmp_path / "rollback.sqlite3"
    with pytest.raises(RuntimeError):
        execute(path, s, truth, observations, admission, interrupt_after=0)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    execute(path, s, truth, observations, admission)
    with pytest.raises(sqlite3.OperationalError):
        execute(path, s, truth, observations, admission)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM balances").fetchone()[0] == 3
    with pytest.raises(ValueError):
        execute(tmp_path / "denied", s, candidate, observations, admission)


def test_corrupted_witness_and_receipt():
    s, candidate, truth = fixture()
    r = run(s, candidate, SyntheticAuthority(s, truth))
    witness = r.initial.witness.model_copy(update={"second": r.initial.witness.first})
    assert not verify_witness(s, (), witness)
    assert not replay(export(r).replace('"seed":0', '"seed":1'))
    with pytest.raises(ValueError):
        replay(" " * 100001)


@pytest.mark.parametrize("seed", range(100))
def test_independent_case_families(seed):
    """Test-owned authority: no production fixture/generator constructs grading truth."""
    import random

    from anomalon_workbench.migration import Account, Link, Plan, Scenario, Scope, select_action

    rng = random.Random(seed + 8181)
    count = 2 + seed % 5
    sources = rng.sample(range(100000, 999999), count)
    destinations = rng.sample(range(1000000, 9999999), count)
    expected_pairs = dict(
        zip((f"owner-{i}" for i in sources), (f"target-{i}" for i in destinations))
    )
    amounts = {s: (500 if seed % 3 == 0 else rng.randint(-10000, 10000)) for s in expected_pairs}
    source_order = list(expected_pairs)
    destination_order = list(expected_pairs.values())
    rng.shuffle(source_order)
    rng.shuffle(destination_order)
    scenario = Scenario(
        seed=seed,
        scope=Scope(snapshot="v1", roster="v1", crosswalk="v1"),
        accounts=tuple(Account(id=s, cents=amounts[s]) for s in source_order),
        destinations=tuple(destination_order),
    )
    truth = Plan(
        version=1, links=tuple(Link(source=s, destination=d) for s, d in expected_pairs.items())
    )
    wrong_links = list(truth.links)
    x, y = wrong_links[:2]
    wrong_links[:2] = [
        Link(source=x.source, destination=y.destination),
        Link(source=y.source, destination=x.destination),
    ]
    wrong = Plan(version=1, links=tuple(wrong_links))
    evidence = (Observation(scope=scenario.scope, links=truth.links),)
    assert evaluate(scenario, truth, evidence).ownership == Verdict.SUPPORTED
    assert evaluate(scenario, wrong, evidence).ownership == Verdict.REFUTED
    assert select_action(scenario, ()).kind != "repeat_total"
    partial = (Observation(scope=scenario.scope, links=truth.links[:1]),)
    assert evaluate(scenario, truth, partial).ownership in (
        Verdict.SUPPORTED,
        Verdict.UNDERDETERMINED,
    )
    r = run(scenario, wrong, SyntheticAuthority(scenario, truth))
    assert dict(r.execution.rows) == {d: amounts[s] for s, d in expected_pairs.items()}
    if seed % 3 == 0:
        assert r.preview.rows == r.execution.rows  # exact identity error; no monetary-harm claim


def test_faults_metadata_and_offline_replay_boundaries(monkeypatch):
    import json

    from anomalon_workbench.domain import canonical, digest
    from anomalon_workbench.migration import Link

    s, candidate, truth = fixture()
    bad = Observation(scope=s.scope, links=(Link(source="unknown", destination=s.destinations[0]),))
    ev = evaluate(s, candidate, (bad,))
    assert ev.evidence_status == ("invalid",) and ev.ownership == Verdict.UNDERDETERMINED
    conflicting = run(s, candidate, SyntheticAuthority(s, truth, "contradictory"))
    assert conflicting.final.ownership == Verdict.INCONSISTENT
    assert conflicting.execution is None and replay(export(conflicting))

    class Down:
        def obtain(self, scope, action):
            raise TimeoutError("external secret text must never be recorded")

    missing = run(s, candidate, Down())
    assert missing.final.ownership == Verdict.UNDERDETERMINED
    assert "external secret" not in export(missing)
    absent = run(s, candidate, SyntheticAuthority(s, truth, "missing"))
    assert all(o.links == () for o in absent.observations)
    good = run(s, candidate, SyntheticAuthority(s, truth))
    monkeypatch.setattr(
        "anomalon_workbench.migration_demo.execute", lambda *a, **k: pytest.fail("offline executed")
    )
    monkeypatch.setattr(
        SyntheticAuthority, "obtain", lambda *a, **k: pytest.fail("offline queried")
    )
    assert replay(export(good))
    bundle = json.loads(export(good))
    bundle["receipt"]["execution"]["committed"] = False
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(canonical(bundle))


def test_import_adversarial_contract():
    import json

    from anomalon_workbench.domain import canonical, digest

    s, candidate, truth = fixture()
    good = run(s, candidate, SyntheticAuthority(s, truth))
    for field in (
        "identity_coverage",
        "total_preserved",
        "row_count_preserved",
        "execution_conforms",
        "ownership_preserved",
    ):
        bundle = json.loads(export(good))
        bundle["receipt"]["execution"][field] = False
        bundle["sha256"] = digest(bundle["receipt"])
        assert not replay(canonical(bundle))
    bundle = json.loads(export(good))
    for key in ("execution", "repaired", "admission"):
        bundle["receipt"][key] = None
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(canonical(bundle))
    for raw in ("[]", "null", '"text"', '{"receipt":{},"receipt":{}}', "[" * 2000 + "]" * 2000):
        with pytest.raises(ValueError):
            replay(raw)


def test_scope_admission_input_bounds_and_build_proof(tmp_path, monkeypatch):
    from pydantic import ValidationError

    from anomalon_workbench.migration import Account, Plan, Scenario, Scope
    from anomalon_workbench.migration_proof import proof_status

    s, candidate, truth = fixture()
    evidence = (Observation(scope=s.scope, links=truth.links),)
    approval = admit(s, truth, evidence)
    changed = s.model_copy(update={"scope": s.scope.model_copy(update={"snapshot": "s2"})})
    assert evaluate(changed, truth, evidence).evidence_status == ("stale",)
    with pytest.raises(ValueError):
        execute(tmp_path / "changed.sqlite3", changed, truth, evidence, approval)
    with pytest.raises(ValueError):
        execute(tmp_path / "proposed.sqlite3", s, truth, evidence)
    for amount in (True, 1.5, 1_000_000_001):
        with pytest.raises(ValidationError):
            Account(id="x", cents=amount)
    with pytest.raises(ValidationError):
        Scope(snapshot="s", roster="r", crosswalk="c", unit="dollar")
    with pytest.raises(ValidationError):
        Scenario(seed=0, scope=s.scope, accounts=s.accounts * 3, destinations=s.destinations * 3)
    assert (
        evaluate(s, Plan(version=1, links=truth.links[:1]), evidence).ownership
        == Verdict.NOT_EVALUATED
    )
    monkeypatch.chdir(tmp_path)
    assert proof_status()["status"] == "not_verified_for_this_build"


def test_cli_and_staged_evidence_reuse(monkeypatch, tmp_path, capsys):
    from anomalon_workbench.migration_demo import main

    s, candidate, truth = fixture()
    authority = SyntheticAuthority(s, truth)
    preview = run(s, candidate, authority, acquire=False)
    assert not preview.steps and not preview.execution and replay(export(preview))
    repaired = run(s, candidate, authority, prior=preview, one_action=True)
    assert repaired.preview == preview.preview and repaired.execution.ownership_preserved
    output = tmp_path / "cli.json"
    monkeypatch.setattr("sys.argv", ["owed-migration", "--output", str(output)])
    main()
    monkeypatch.setattr("sys.argv", ["owed-migration", "--replay", str(output)])
    main()
    assert '"offline_replay_matched": true' in capsys.readouterr().out
