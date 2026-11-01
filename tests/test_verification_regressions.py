import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from anomalon_workbench.domain import digest
from anomalon_workbench.migration import Observation
from anomalon_workbench.migration_demo import export, fixture, run
from anomalon_workbench.migration_proof import proof_status


@pytest.mark.parametrize("mode", ["observed", "stale", "unavailable"])
def test_overbroad_response_rejected_before_admission(monkeypatch, mode):
    scenario, candidate, truth = fixture(0, 4)

    class Overbroad:
        def obtain(self, scope, action):
            assert action.kind == "source"
            if mode == "stale":
                scope = scope.model_copy(update={"crosswalk": "old"})
            return Observation(scope=scope, links=truth.links,
                               status="unavailable" if mode == "unavailable" else "observed")

    monkeypatch.setattr("anomalon_workbench.migration_demo.admit",
                        lambda *a, **k: pytest.fail("Overbroad evidence reached admission"))
    with pytest.raises(ValueError, match="evidence_response_contract"):
        run(scenario, candidate, Overbroad())


@pytest.mark.parametrize("transition", ["another_case", "acquire", "restart"])
def test_replay_badge_belongs_to_exact_receipt(monkeypatch, transition):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_AUTH_ENABLED", "false")
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()

    def click(label):
        next(b for b in app.button if b.label == label).click().run()
        assert not app.exception

    click("Run the migration challenge")
    click("Replay this receipt offline")
    assert any("Offline semantic replay matched" in m.value for m in app.markdown)
    if transition == "another_case":
        click("Generate another reproducible case")
        click("Run the migration challenge")
    elif transition == "acquire":
        click("Obtain selected evidence and apply justified repair")
    else:
        click("Run the migration challenge")
    assert not any("Offline semantic replay matched" in m.value for m in app.markdown)
    assert "migration_replay" not in app.session_state
    click("Replay this receipt offline")
    assert app.session_state["migration_replay"] == {
        "receipt_digest": digest(app.session_state["migration_receipt"]), "matched": True
    }


@pytest.mark.parametrize("fault", ["empty", "missing_source", "missing_theorem", "bad_version",
                                   "bad_exit", "bad_axiom", "malformed", "mismatched_source",
                                   "missing_output", "missing_command", "wrong_command",
                                   "extra_source", "bad_hash", "empty_theorems", "audit_mismatch",
                                   "missing_audit", "placeholder", "unknown_field", "wrong_pin",
                                   "duplicate_json", "invalid_utf8", "oversized", "top_level_list"])
def test_unverified_proof_reports_fail_closed(tmp_path, monkeypatch, fault):
    root = Path(__file__).parents[1]
    report = json.loads((root / "evidence/migration-lean.json").read_text(encoding="utf-8"))
    for name in ("lean/Migration.lean", "lean/lean-toolchain"):
        target = tmp_path / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    if fault == "empty":
        report["source_sha256"] = {}
        for name in ("lean/Migration.lean", "lean/lean-toolchain"):
            (tmp_path / name).unlink()
    elif fault == "missing_source":
        report["source_sha256"].pop("lean/lean-toolchain")
    elif fault == "missing_theorem":
        report["theorems"].pop("ownership")
    elif fault == "bad_version":
        report["version"] = "Lean (version 4.20.0, test)"
    elif fault == "bad_exit":
        report["exit_status"] = False
    elif fault == "bad_axiom":
        report["theorems"]["ownership"] = ["sorryAx"]
    elif fault == "malformed":
        report["source_sha256"] = []
    elif fault == "mismatched_source":
        (tmp_path / "lean/Migration.lean").write_text("changed")
    elif fault in ("missing_output", "missing_command"):
        report.pop(fault.removeprefix("missing_"))
    elif fault == "wrong_command":
        report["command"] = ["lean", "Other.lean"]
    elif fault == "extra_source":
        report["source_sha256"]["unapproved-file"] = "0" * 64
    elif fault == "bad_hash":
        report["source_sha256"]["lean/Migration.lean"] = "not a hash"
    elif fault == "empty_theorems":
        report["theorems"] = {}
    elif fault == "audit_mismatch":
        report["theorems"]["conservation"] = []
    elif fault == "missing_audit":
        report["output"] = "\n".join(line for line in report["output"].splitlines() if "depends on axioms" not in line)
    elif fault == "placeholder":
        report["output"] += "\nsorryAx"
    elif fault == "unknown_field":
        report["unrecognized"] = "value"
    elif fault == "wrong_pin":
        import hashlib
        pin = tmp_path / "lean/lean-toolchain"
        pin.write_text("leanprover/lean4:v4.20.0")
        report["source_sha256"]["lean/lean-toolchain"] = hashlib.sha256(pin.read_bytes()).hexdigest()
    (tmp_path / "evidence").mkdir()
    raw = json.dumps(report).encode()
    if fault == "duplicate_json":
        raw = raw[:-1] + b',"status":"verified_during_build"}'
    elif fault == "invalid_utf8":
        raw = b"\xff"
    elif fault == "oversized":
        raw = b" " * 100001
    elif fault == "top_level_list":
        raw = b"[]"
    (tmp_path / "evidence/migration-lean.json").write_bytes(raw)
    monkeypatch.chdir(tmp_path)
    assert proof_status() == {"status": "not_verified_for_this_build"}


def test_valid_proof_report_matches_exact_artifact():
    import hashlib

    status = proof_status()
    assert status["status"] == "verified_during_build"
    assert status["artifact_sha256"] == hashlib.sha256(Path("evidence/migration-lean.json").read_bytes()).hexdigest()


def test_ordinary_generated_receipt_still_replays():
    from anomalon_workbench.migration_demo import SyntheticAuthority, replay

    for count in range(2, 7):
        scenario, candidate, truth = fixture(77, count)
        receipt = run(scenario, candidate, SyntheticAuthority(scenario, truth))
        assert replay(export(receipt))


def test_overbroad_historical_receipt_cannot_be_resumed(monkeypatch):
    from anomalon_workbench.migration import evaluate
    from anomalon_workbench.migration_demo import Step, SyntheticAuthority, replay
    from anomalon_workbench.migration_execution import admit

    scenario, candidate, truth = fixture(0, 4)
    good = run(scenario, candidate, SyntheticAuthority(scenario, truth))
    observation = Observation(scope=scenario.scope, links=truth.links)
    bad = good.model_copy(update={
        "steps": (Step(action=good.steps[0].action, observation=observation),),
        "observations": (observation,),
        "final": evaluate(scenario, candidate, (observation,)),
        "admission": admit(scenario, good.repaired, (observation,)),
        "run_id": digest({"scenario": digest(scenario), "candidate": digest(candidate),
                          "evidence": [digest(observation)]}),
    })
    assert not replay(export(bad))
    monkeypatch.setattr("anomalon_workbench.migration_demo.admit",
                        lambda *a, **k: pytest.fail("Invalid history reached admission"))
    with pytest.raises(ValueError, match="invalid_prior_receipt"):
        run(scenario, candidate, SyntheticAuthority(scenario, truth), prior=bad)
