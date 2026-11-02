"""Independent interaction and custody checks for visitor-selected investigations."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from anomalon_workbench.domain import digest
from anomalon_workbench.migration import EvidenceAction
from anomalon_workbench.migration_demo import SyntheticAuthority, export, fixture, replay, run
from anomalon_workbench.migration_scene import scene_html


def app_start(monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_AUTH_ENABLED", "false")
    return AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()


def click(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception
    return app


def predict(app, answer="Not enough information"):
    click(app, "Inspect the proposal")
    click(app, "Make your prediction")
    app.radio(key="migration_prediction").set_value(answer).run()
    click(app, "Test my prediction")
    return app


def investigate(app, choice, source=None):
    app.selectbox(key="migration_investigation").set_value(choice).run()
    if source:
        app.selectbox(key="migration_source").set_value(source).run()
    return click(app, "Run this investigation")


def test_public_guided_migration_session_and_replay(monkeypatch):
    app = app_start(monkeypatch)
    assert not app.exception
    text = "\n".join(m.value for m in app.markdown)
    assert text.count('class="an-card__owner">Owner not established') == 3
    assert "Possible assignment A" not in text
    predict(app)
    receipt = app.session_state["migration_receipt"]
    assert receipt.steps == () and receipt.initial.compatible_count == 6
    assert "Possible assignment A" in "\n".join(m.value for m in app.markdown)
    assert not any(
        "wrong accounts" in m.value or "proposal: rejected" in m.value for m in app.markdown
    )
    investigate(app, "Ask Owed to choose")
    receipt = app.session_state["migration_receipt"]
    assert receipt.execution.ownership_preserved
    assert receipt.steps[-1].selected_by == "engine"
    click(app, "Verify the result")
    assert "\n".join(m.value for m in app.markdown).count('class="an-check-row"') == 6
    click(app, "Replay this receipt offline")
    assert app.session_state["migration_replay"] == {
        "receipt_digest": digest(receipt),
        "matched": True,
    }
    click(app, "Restart the walkthrough")
    assert "migration_receipt" not in app.session_state
    assert "migration_replay" not in app.session_state
    assert not app.exception


@pytest.mark.parametrize("answer", ["Yes", "No", "Not enough information"])
def test_prediction_never_requires_a_contrived_failure(monkeypatch, answer):
    app = predict(app_start(monkeypatch), answer)
    feedback = app.session_state["migration_feedback"]
    assert "ownership" in feedback or "owner" in feedback
    if answer != "Yes":
        assert "You identified" in feedback
    assert app.session_state["migration_phase"] == 3


def test_repeated_checks_add_no_evidence_and_partial_record_eliminates_four(monkeypatch):
    app = predict(app_start(monkeypatch))
    initial = app.session_state["migration_receipt"]
    for choice in ["Check the total again", "Count the accounts again"]:
        investigate(app, choice)
        assert app.session_state["migration_receipt"] == initial
        assert "none eliminated" in app.session_state["migration_report"]
        status = next(m.value for m in app.markdown if 'class="an-status' in m.value)
        assert "0 eliminated by last check" in status
    source = sorted(a.id for a in initial.scenario.accounts)[0]
    investigate(app, "Request one identity record", source)
    receipt = app.session_state["migration_receipt"]
    assert receipt.final.compatible_count == 2
    assert "4 eliminated by last check" in next(
        m.value for m in app.markdown if 'class="an-status' in m.value
    )
    assert receipt.execution is None
    assert receipt.steps[-1].selected_by == "visitor"
    assert replay(export(receipt))
    text = "\n".join(m.value for m in app.markdown)
    assert text.count('class="an-card__owner">Owner not established') == 2
    investigate(app, "Request the full identity mapping")
    assert app.session_state["migration_receipt"].execution.ownership_preserved
    assert replay(export(app.session_state["migration_receipt"]))


@pytest.mark.parametrize("mode", ["missing", "stale", "contradictory"])
def test_public_missing_stale_and_conflicting_modes(monkeypatch, mode):
    app = app_start(monkeypatch)
    app.selectbox(key="migration_mode").set_value(mode).run()
    predict(app)
    investigate(app, "Request the full identity mapping")
    receipt = app.session_state["migration_receipt"]
    assert receipt.execution is None
    assert replay(export(receipt))
    if mode == "missing":
        assert any("source did not supply" in w.value for w in app.warning)
        assert receipt.final.compatible_count == 6
    if mode == "contradictory":
        assert any("Resolve the conflicting" in e.value for e in app.error)
        assert receipt.final.compatible_count == 0
    if mode == "stale":
        assert receipt.final.compatible_count == 6
        click(app, "Refresh identity records")
        assert app.session_state["migration_receipt"].execution.ownership_preserved
        assert replay(export(app.session_state["migration_receipt"]))


def test_visitor_actions_are_replayed_without_claiming_engine_selection():
    s, candidate, truth = fixture()
    source = sorted(a.id for a in s.accounts)[0]
    request = EvidenceAction(kind="source", source=source, cost=2)
    receipt = run(s, candidate, SyntheticAuthority(s, truth), requested_action=request)
    assert len(receipt.steps) == 1 and receipt.steps[0].selected_by == "visitor"
    assert replay(export(receipt))
    bundle = json.loads(export(receipt))
    bundle["receipt"]["steps"][0]["selected_by"] = "engine"
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(json.dumps(bundle))
    bundle["receipt"]["steps"][0]["selected_by"] = "visitor"
    bundle["receipt"]["schema_version"] = bundle["receipt"]["checker"] = "migration/1"
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(json.dumps(bundle))


def test_legacy_receipt_without_selector_field_still_replays():
    s, candidate, truth = fixture()
    bundle = json.loads(export(run(s, candidate, SyntheticAuthority(s, truth))))
    bundle["receipt"]["schema_version"] = bundle["receipt"]["checker"] = "migration/1"
    for step in bundle["receipt"]["steps"]:
        del step["selected_by"]
    bundle["sha256"] = digest(bundle["receipt"])
    assert replay(json.dumps(bundle))
    historical = Path(__file__).parents[1] / "examples/migration/repaired.json"
    assert replay(historical.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "visitor_request",
    [
        EvidenceAction(kind="repeat_total", cost=0),
        EvidenceAction(kind="source", source="unknown", cost=2),
        EvidenceAction(kind="full_crosswalk", cost=0),
    ],
)
def test_invalid_manual_request_rejected_before_authority(visitor_request):
    s, candidate, truth = fixture()
    with pytest.raises(ValueError, match="invalid_visitor"):
        run(s, candidate, SyntheticAuthority(s, truth), requested_action=visitor_request)


def test_scene_escapes_data_and_has_accessible_mobile_relationships():
    markup = scene_html(
        [{"id": "x", "name": "<script>alert(1)</script>", "balance": "$1"}],
        [{"id": "n", "balance": "$1", "owner": "Owner not established"}],
        [{"source": "x", "destination": "n", "kind": "proposed"}],
        title="Proposal",
        caption="Not established",
    )
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
    assert 'class="an-rel"' in markup and "Proposed:" in markup
