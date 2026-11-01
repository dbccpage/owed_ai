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
    expected = {p.destination: a.cents for p in truth.links for a in scenario.accounts
                if a.id == p.source}
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
    conflicting = (Observation(scope=s.scope, links=truth.links),
                   Observation(scope=s.scope, links=candidate.links))
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
