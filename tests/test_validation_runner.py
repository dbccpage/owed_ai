import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def runner_module():
    spec = importlib.util.spec_from_file_location(
        "live_validation", Path(__file__).parents[1] / "scripts/live_validation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validation_does_not_promote_failure_or_missing_replay():
    successful = runner_module().successful
    assert not successful([])
    assert not successful([{"status": "failed", "replay_matched": True}])
    assert not successful([{"status": "completed", "replay_matched": False}])
    assert successful([{"status": "completed", "replay_matched": True}])


def test_failed_attempts_are_preserved_and_main_exits_nonzero(tmp_path, monkeypatch):
    runner = runner_module()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["live_validation.py", "--provider", "openrouter", "--model", "test"]
    )
    monkeypatch.setattr(
        runner.ProviderConfig,
        "from_env",
        lambda *_: SimpleNamespace(public=lambda: {"provider": "test"}),
    )
    receipt = {"status": "failed", "result": {"execution_error": "authentication_failed"}}
    report = {
        "status": "failed",
        "replay_matched": True,
        "execution_error": "authentication_failed",
        "lab": "ledger",
    }
    monkeypatch.setattr(runner, "run_case", lambda *_: (receipt, report))
    assert runner.main() == 1
    assert runner.main() == 1
    attempts = list((tmp_path / "examples/attempts/openrouter").glob("*/ledger.json"))
    assert len(attempts) == 2
    assert all(json.loads(p.read_text(encoding="utf-8"))["receipt"] == receipt for p in attempts)
    assert not list((tmp_path / "examples/live/openrouter").glob("*.json"))
    summary = json.loads((tmp_path / "evidence/openrouter-live.json").read_text(encoding="utf-8"))
    assert summary["requested_scope_passed"] is False
