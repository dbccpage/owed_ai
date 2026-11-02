from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from test_migration_ui import click, investigate, predict

from anomalon_workbench.migration import Account
from anomalon_workbench.migration_demo import fixture
from anomalon_workbench.migration_ui import dollars, source_commit


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_AUTH_ENABLED", "false")
    return AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()


def test_same_scene_shows_the_actual_repair(app):
    assert any("Interactive demo—no account required" in c.value for c in app.caption)
    predict(app)
    investigate(app, "Ask Owed to choose")
    text = "\n".join(m.value for m in app.markdown)
    assert "Was $100" in text and "Was $200" in text and "Was $700" in text
    assert "Verified against SQLite (original run)" in text
    assert "an-conn__line--verified" in text
    assert "Repaired proposal" not in text  # A result is shown with its objects, not just a banner.


def test_changing_scenario_invalidates_result_and_replay(app):
    predict(app)
    investigate(app, "Ask Owed to choose")
    click(app, "Replay this receipt offline")
    app.selectbox(key="migration_mode").set_value("contradictory").run()
    assert "migration_receipt" not in app.session_state
    assert "migration_replay" not in app.session_state
    assert app.session_state.get("migration_phase", 0) == 0


def test_equal_balances_do_not_claim_financial_loss(app, monkeypatch):
    scenario, candidate, authority = fixture()
    equal = scenario.model_copy(
        update={"accounts": tuple(Account(id=a.id, cents=10000) for a in scenario.accounts)}
    )
    monkeypatch.setattr(
        "anomalon_workbench.migration_ui.fixture", lambda seed: (equal, candidate, authority)
    )
    predict(app)
    investigate(app, "Ask Owed to choose")
    text = "\n".join(m.value for m in app.markdown)
    assert "incorrectly" not in text and "Was $100" not in text
    assert any("Some balances are equal" in i.value for i in app.info)


def test_secondary_pages_keep_json_out_of_the_guided_scene(app):
    predict(app)
    assert len(app.json) == 0
    nav = next(r for r in app.sidebar.radio if r.label == "Workbench")
    nav.set_value("Explanation").run()
    assert not app.exception and any("Why a correct total" in t.value for t in app.title)
    nav = next(r for r in app.sidebar.radio if r.label == "Workbench")
    nav.set_value("Technical evidence").run()
    assert not app.exception and len(app.json) > 0
    click(app, "Change snapshot and crosswalk version")
    assert any("remains history" in w.value for w in app.warning)


@pytest.mark.parametrize(
    "cents, expected",
    [(0, "$0"), (-1, "-$0.01"), (100001, "$1,000.01"), (2**63 - 1, "$92,233,720,368,547,758.07")],
)
def test_money_remains_exact(cents, expected):
    assert dollars(cents) == expected


@pytest.mark.parametrize(
    "value, expected",
    [("a" * 40, "a" * 40), ("c87c0c2a", None), ("not-a-commit", None), ("", None)],
)
def test_source_commit_is_explicit_runtime_metadata(monkeypatch, value, expected):
    monkeypatch.setenv("RENDER_GIT_COMMIT", value)
    assert source_commit() == expected


def test_authentication_is_in_collapsed_operator_section(app):
    section = next(
        e for e in app.sidebar.expander if e.label == "Operator access and live experiments"
    )
    assert not section.proto.expanded
    assert any("Live experiments are currently disabled" in c.value for c in section.caption)
