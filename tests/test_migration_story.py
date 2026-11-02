from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from anomalon_workbench.migration import Account
from anomalon_workbench.migration_demo import fixture
from anomalon_workbench.migration_ui import dollars, source_commit


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_AUTH_ENABLED", "false")
    return AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()


def click(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception


def balance_table(app):
    return next(t.value for t in app.table if "Corrected balance" in t.value.columns)


def test_one_table_explains_default_repair(app):
    assert any("Interactive demo—no account required" in c.value for c in app.caption)
    assert not any(e.selectbox for e in app.expander)
    click(app, "Run the migration challenge")
    assert set(balance_table(app)["Corrected balance"]) == {"Not established"}
    assert any("A correct total does not establish correct ownership" in i.value for i in app.info)
    click(app, "Obtain selected evidence and apply justified repair")
    assert balance_table(app).to_dict("records") == [
        {"Account": "N-0-0", "Proposed balance": "$100", "Corrected balance": "$700"},
        {"Account": "N-0-1", "Proposed balance": "$200", "Corrected balance": "$100"},
        {"Account": "N-0-2", "Proposed balance": "$700", "Corrected balance": "$200"},
    ]
    text = "\n".join(m.value for m in app.markdown)
    assert "Every balance was assigned incorrectly. Both versions total $1,000." in text
    assert "Original proposal: rejected." in text
    assert "Repaired proposal: verified against current evidence." in text
    assert "Remaining obligation:" not in text
    assert any("checked against the resulting database" in s.value for s in app.success)
    assert not any(b.label == "Run with live model" for b in app.button)


@pytest.mark.parametrize("mode", ["missing", "stale", "contradictory"])
def test_blocked_scenarios_do_not_claim_corrected_balances(app, mode):
    app.selectbox[0].set_value(mode).run()
    click(app, "Run the migration challenge")
    click(app, "Obtain selected evidence and apply justified repair")
    assert set(balance_table(app)["Corrected balance"]) == {"Not established"}
    assert not app.session_state["migration_receipt"].execution
    assert not any("Repaired proposal: verified" in m.value for m in app.markdown)
    if mode == "contradictory":
        assert any("Resolve the conflicting identity records before proceeding" in e.value for e in app.error)


def test_changing_visible_scenario_invalidates_result_and_replay(app):
    click(app, "Run the migration challenge")
    click(app, "Obtain selected evidence and apply justified repair")
    click(app, "Replay this receipt offline")
    app.selectbox[0].set_value("contradictory").run()
    assert "migration_receipt" not in app.session_state
    assert "migration_replay" not in app.session_state
    assert not any("Original proposal:" in m.value for m in app.markdown)


def test_equal_balances_do_not_claim_financial_loss(app, monkeypatch):
    scenario, candidate, authority = fixture()
    equal = scenario.model_copy(update={"accounts": tuple(Account(id=a.id, cents=10000) for a in scenario.accounts)})
    monkeypatch.setattr("anomalon_workbench.migration_ui.fixture", lambda seed: (equal, candidate, authority))
    click(app, "Run the migration challenge")
    click(app, "Obtain selected evidence and apply justified repair")
    text = "\n".join(m.value for m in app.markdown)
    assert "displayed balances did not" in text
    assert "Every balance was assigned incorrectly" not in text


@pytest.mark.parametrize("cents, expected", [(0, "$0"), (-1, "-$0.01"), (100001, "$1,000.01"),
                                            (2**63 - 1, "$92,233,720,368,547,758.07")])
def test_money_remains_exact(cents, expected):
    assert dollars(cents) == expected


@pytest.mark.parametrize("value, expected", [("a" * 40, "a" * 40), ("c87c0c2a", None),
                                           ("not-a-commit", None), ("", None)])
def test_source_commit_is_explicit_runtime_metadata(monkeypatch, value, expected):
    monkeypatch.setenv("RENDER_GIT_COMMIT", value)
    assert source_commit() == expected


def test_authentication_is_in_collapsed_operator_section(app):
    section = next(e for e in app.sidebar.expander if e.label == "Operator access and live experiments")
    assert not section.proto.expanded
    assert any("Live experiments are currently disabled" in c.value for c in section.caption)
