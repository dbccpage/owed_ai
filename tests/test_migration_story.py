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
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()
    return app.sidebar.radio[0].set_value("Migration challenge").run()


@pytest.fixture
def one_screen_app(monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_AUTH_ENABLED", "false")
    return AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()


def balance_table(app):
    return next(t.value for t in app.table if "Corrected balance" in t.value.columns)


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


def test_one_screen_table_explains_default_repair(one_screen_app):
    assert any("Interactive demo—no account required" in c.value for c in one_screen_app.caption)
    click(one_screen_app, "Run the migration challenge")
    assert set(balance_table(one_screen_app)["Corrected balance"]) == {"Not established"}
    assert any(
        "A correct total does not establish correct ownership" in i.value
        for i in one_screen_app.info
    )
    click(one_screen_app, "Obtain selected evidence and apply justified repair")
    assert balance_table(one_screen_app).to_dict("records") == [
        {"Account": "N-0-0", "Proposed balance": "$100", "Corrected balance": "$700"},
        {"Account": "N-0-1", "Proposed balance": "$200", "Corrected balance": "$100"},
        {"Account": "N-0-2", "Proposed balance": "$700", "Corrected balance": "$200"},
    ]
    text = "\n".join(m.value for m in one_screen_app.markdown)
    assert "Every balance was assigned incorrectly. Both versions total $1,000." in text
    assert "Original proposal: rejected." in text
    assert "Repaired proposal: verified against current evidence." in text
    assert any("checked against the resulting database" in s.value for s in one_screen_app.success)


@pytest.mark.parametrize("mode", ["missing", "stale", "contradictory"])
def test_one_screen_blocked_scenarios_do_not_claim_corrected_balances(one_screen_app, mode):
    one_screen_app.selectbox(key="migration_mode").set_value(mode).run()
    click(one_screen_app, "Run the migration challenge")
    click(one_screen_app, "Obtain selected evidence and apply justified repair")
    assert set(balance_table(one_screen_app)["Corrected balance"]) == {"Not established"}
    assert not one_screen_app.session_state["migration_receipt"].execution
    assert not any("Repaired proposal: verified" in m.value for m in one_screen_app.markdown)
    if mode == "contradictory":
        assert any(
            "Resolve the conflicting identity records before proceeding" in e.value
            for e in one_screen_app.error
        )


def test_one_screen_five_elements_and_more_control(one_screen_app):
    required_labels = [
        "1. The claim: the total is right",
        "2. The check that fails: which balances, which accounts",
        "3. What the machine does not know and what it would cost to find out",
        "4. The question it asks",
        "5. The corrected result with the rows that changed",
    ]
    for state in ("initial", "repaired"):
        if state == "repaired":
            click(one_screen_app, "Run the migration challenge")
            click(one_screen_app, "Obtain selected evidence and apply justified repair")
        full_text = "\n".join(
            [h.value for h in one_screen_app.subheader] + [m.value for m in one_screen_app.markdown]
        )
        positions = []
        for label in required_labels:
            assert label in full_text, f"Missing label ({state}): {label}"
            positions.append(full_text.index(label))
        assert positions == sorted(positions), (
            f"Five elements must appear in exact order 1..5 ({state})"
        )
        assert "Source:" in full_text and "Rule:" in full_text
        main_expanders = [e.label for e in one_screen_app.main.expander]
        assert main_expanders == ["More"], (
            f"Expected only ['More'] expander on main screen ({state}), got {main_expanders}"
        )
