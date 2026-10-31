import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from anomalon_workbench.domain import ModelReply, ProviderFailure, RunSpec, canonical, json_object
from anomalon_workbench.examples import ledger_example
from anomalon_workbench.hosting import (
    HostedPolicy,
    Principal,
    hosted_mode,
    private_store,
    submit_hosted,
)
from anomalon_workbench.serve import auth_document
from anomalon_workbench.spending import MeteredProvider, SpendLedger


@pytest.fixture
def hosted(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "true")
    monkeypatch.setenv("WORKBENCH_AUTH_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("WORKBENCH_ALLOWED_SUBJECTS", '["alice","bob"]')
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-credential")
    return HostedPolicy.from_env()


def identity(policy, subject="alice", **extra):
    return policy.authenticate(True, {
        "iss": policy.issuer, "sub": subject, "exp": int(time.time()) + 3600, **extra,
    })


@pytest.mark.parametrize("claims", [
    {"sub": "outsider"}, {"iss": "https://wrong.example"}, {"exp": 1},
    {"exp": True}, {"exp": "9999999999"}, {"sub": "../alice"},
])
def test_identity_rejects_wrong_issuer_unknown_subject_and_expiry(hosted, claims):
    with pytest.raises(ValueError, match="live_access_denied"):
        identity(hosted, **claims)
    with pytest.raises(ValueError):
        hosted.authenticate(False, {})


def test_render_cannot_start_in_local_mode(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("WORKBENCH_MODE", "local")
    with pytest.raises(ValueError):
        hosted_mode()


def test_tenant_store_and_prompt_isolation(hosted):
    alice, bob = private_store(identity(hosted)), private_store(identity(hosted, "bob"))
    spec = json_object(RunSpec(lab="ledger", payload=json_object(ledger_example())))
    run = alice.enqueue("same-request", spec, {})
    assert bob.list_runs() == []
    for operation in (bob.get, bob.admit):
        with pytest.raises(ValueError):
            operation(run, "operator") if operation == bob.admit else operation(run)
    assert alice.root != bob.root
    secret_artifact = alice.artifact({"private": "alice only"})
    with pytest.raises(FileNotFoundError):
        bob.read(secret_artifact)
    assert bob.active_prompt() is None
    bob.cancel(run)
    assert not alice.cancelled(run)
    assert alice.claim(run, 1)
    alice.finish(run, "completed", {"result": {"eligible": True, "child": {"instructions": "test-only candidate"}}})
    alice.admit(run, "operator")
    assert alice.active_prompt()["instructions"] == "test-only candidate"
    assert bob.active_prompt() is None
    with pytest.raises(ValueError):
        private_store(Principal(owner="../alice", expires=int(time.time()) + 60))


def test_submit_rechecks_allowlist_and_ignores_visitor_provider_env(hosted, monkeypatch):
    principal = identity(hosted)
    monkeypatch.setenv("WORKBENCH_BASE_URL", "http://localhost:9999")
    monkeypatch.setenv("WORKBENCH_PROVIDER", "local")
    monkeypatch.setenv("WORKBENCH_MODEL", "expensive-model")
    launched = Mock()
    monkeypatch.setattr("anomalon_workbench.worker.launch", launched)
    spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
    run = submit_hosted(principal, spec, "request")
    assert submit_hosted(principal, spec, "request") == run
    assert launched.call_count == 1
    store = private_store(principal)
    config = store.read(store.get(run)["config_hash"])
    assert config["provider"] == "openrouter"
    assert config["base_url"] == "https://openrouter.ai/api/v1"
    assert config["model"] == "openai/gpt-4.1-mini"
    monkeypatch.setenv("WORKBENCH_ALLOWED_SUBJECTS", '[]')
    with pytest.raises(ValueError):
        submit_hosted(principal, spec, "revoked")


def test_concurrent_reservations_never_cross_daily_limit(hosted, tmp_path):
    policy = hosted.model_copy(update={"daily_microdollars": 300_000,
                                       "user_daily_microdollars": 300_000})
    ledger = SpendLedger(tmp_path / "control")
    ledger.admit_run("run", "alice", policy, 300)

    def reserve(_):
        try:
            return SpendLedger(tmp_path / "control").reserve("run", "alice", policy)
        except ProviderFailure:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(12)))
    assert len([r for r in results if r]) == 3
    assert ledger.usage("alice")["charged_microdollars"] == 300_000


def test_shared_user_caps_and_concurrency(hosted, tmp_path):
    ledger = SpendLedger(tmp_path / "control")
    assert ledger.admit_run("a", "alice", hosted, 300)
    with pytest.raises(ValueError, match="concurrency"):
        ledger.admit_run("b", "bob", hosted, 300)
    policy = hosted.model_copy(update={"user_daily_requests": 1})
    ledger.reserve("a", "alice", policy)
    with pytest.raises(ProviderFailure, match="spending_limit"):
        ledger.reserve("a", "alice", policy)
    ledger.release_run("a")
    assert ledger.admit_run("b", "bob", policy, 300)
    ledger.reserve("b", "bob", policy)
    assert ledger.usage("bob")["requests"] == 1
    with pytest.raises(ProviderFailure, match="lease"):
        ledger.reserve("b", "alice", policy)


def test_uncertain_cost_retained_restart_and_overrun_halts(hosted, tmp_path):
    ledger = SpendLedger(tmp_path / "control")
    ledger.admit_run("r", "alice", hosted, 300)
    pending = ledger.reserve("r", "alice", hosted)
    ledger.settle(pending, None)
    restarted = SpendLedger(tmp_path / "control")
    assert restarted.usage("alice")["charged_microdollars"] == 100_000
    reported = restarted.reserve("r", "alice", hosted)
    restarted.settle(reported, 0.0000001)
    assert restarted.usage("alice")["charged_microdollars"] == 100_001
    with pytest.raises(ValueError):
        restarted.settle(reported, 0.0)
    overrun = restarted.reserve("r", "alice", hosted)
    restarted.settle(overrun, 0.11)
    with pytest.raises(ProviderFailure, match="halted"):
        restarted.reserve("r", "alice", hosted)


def test_meter_blocks_network_after_failure_or_revocation(hosted, tmp_path, monkeypatch):
    principal = identity(hosted)
    ledger = SpendLedger(tmp_path / "control")
    ledger.admit_run("r", principal.owner, hosted, 300)
    provider = Mock()
    provider.generate.side_effect = ProviderFailure("provider_timeout")
    metered = MeteredProvider(provider, ledger, "r", principal)
    with pytest.raises(ProviderFailure, match="timeout"):
        metered.generate("system", "user", {}, 128, 1)
    assert ledger.usage(principal.owner)["uncertain_reservations"] == 1
    monkeypatch.setenv("WORKBENCH_ALLOWED_SUBJECTS", '[]')
    with pytest.raises(ProviderFailure, match="expired_or_disabled"):
        metered.generate("system", "user", {}, 128, 1)
    assert provider.generate.call_count == 1


def test_hosted_worker_validates_context_and_records_real_boundary(hosted, monkeypatch):
    from anomalon_workbench import worker
    from anomalon_workbench.service import replay

    principal = identity(hosted)
    monkeypatch.setattr(worker, "launch", Mock())
    spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
    run = submit_hosted(principal, spec, "worker-request")
    store = private_store(principal)
    provider = Mock()
    provider.generate.return_value = ModelReply(
        content=canonical({"interpretation": "Test double", "verdict": "underdetermined"}),
        cost=0.0005,
    )
    monkeypatch.setattr(worker, "HTTPProvider", lambda config: provider)
    worker.work(store.root, run)
    assert store.get(run)["status"] == "completed"
    assert replay(store.read(store.get(run)["receipt_hash"]))
    assert SpendLedger(store.root.parent.parent / "control").usage(principal.owner)["charged_microdollars"] == 500
    # A direct local-style enqueue cannot bypass hosted worker admission.
    bypass = store.enqueue("bypass", json_object(spec), hosted.provider().public())
    worker.work(store.root, bypass)
    assert store.get(bypass)["status"] == "failed"
    assert provider.generate.call_count == 1


def test_auth_runtime_file_escaping_and_no_secret_output(hosted, monkeypatch):
    import tomllib

    monkeypatch.setenv("WORKBENCH_PUBLIC_URL", "https://workbench.anomalon.com")
    monkeypatch.setenv("WORKBENCH_COOKIE_SECRET", "x" * 32)
    monkeypatch.setenv("WORKBENCH_AUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("WORKBENCH_AUTH_CLIENT_SECRET", 'quoted"\\secret')
    parsed = tomllib.loads(auth_document())
    assert parsed["auth"]["client_secret"] == 'quoted"\\secret'
    assert parsed["auth"]["redirect_uri"] == "https://workbench.anomalon.com/oauth2callback"


def test_public_demo_does_not_open_private_store_or_offer_paid_actions(hosted, monkeypatch):
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setattr("anomalon_workbench.ui.Store", Mock(side_effect=AssertionError("private store")))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run()
    for page in ("Evidence", "Composition", "Revision", "Run inspector"):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
        assert not any(b.label == "Run with live model" for b in app.button)
        assert not any(s.label in ("Provider", "Run") for s in app.selectbox)
        assert not app.get("file_uploader")
    assert any(s.label == "Recorded lab" for s in app.selectbox)
