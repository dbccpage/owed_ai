"""Regression coverage for the external PR #11 code/product review."""

import json
import re
from pathlib import Path

import pytest
from test_migration_ui import app_start, click, investigate, predict

from anomalon_workbench.domain import digest
from anomalon_workbench.migration import (
    EvidenceAction,
    Observation,
    evidence_status,
    response_matches_action,
)
from anomalon_workbench.migration_demo import (
    SyntheticAuthority,
    export,
    fixture,
    investigation_timeline,
    record_probe,
    replay,
    run,
)
from anomalon_workbench.migration_scene import scene_html, stylesheet


@pytest.mark.parametrize("kind", ["source", "full_crosswalk"])
@pytest.mark.parametrize("size", [0, 1, 2])
def test_observed_response_must_fulfil_request_before_admission(monkeypatch, kind, size):
    scenario, original, truth = fixture()
    action = EvidenceAction(
        kind=kind, source=truth.links[0].source if kind == "source" else "", cost=2
    )
    links = truth.links[:size]
    observation = Observation(scope=scenario.scope, links=links)
    valid = kind == "source" and size == 1
    assert response_matches_action(scenario, action, observation) == valid
    if not size:
        assert evidence_status(scenario, observation) == "invalid"

    class Adapter:
        def obtain(self, scope, requested):
            return observation

    if not valid:
        monkeypatch.setattr(
            "anomalon_workbench.migration_demo.admit",
            lambda *a, **k: pytest.fail("Invalid response reached admission"),
        )
        with pytest.raises(ValueError, match="evidence_response_contract"):
            run(scenario, original, Adapter(), requested_action=action)
    else:
        receipt = run(scenario, original, Adapter(), requested_action=action)
        assert receipt.final.compatible_count == 2 and receipt.execution is None


def test_complete_conflicting_response_remains_a_conflict():
    scenario, original, truth = fixture()
    action = EvidenceAction(kind="full_crosswalk", cost=2)
    authority = SyntheticAuthority(scenario, truth, "contradictory")
    observation = authority.obtain(scenario.scope, action)
    assert response_matches_action(scenario, action, observation)
    assert {p.source for p in observation.links} == {a.id for a in scenario.accounts}
    receipt = run(scenario, original, authority)
    assert receipt.final.conflicts and receipt.final.compatible_count == 0
    assert receipt.execution is None and replay(export(receipt))


def test_unavailable_and_stale_are_distinct_from_incomplete_observed():
    scenario, original, truth = fixture()
    action = EvidenceAction(kind="full_crosswalk", cost=2)
    for mode, status in [("missing", "unavailable"), ("stale", "stale")]:
        observation = SyntheticAuthority(scenario, truth, mode).obtain(scenario.scope, action)
        assert response_matches_action(scenario, action, observation)
        assert evidence_status(scenario, observation) == status
        receipt = run(scenario, original, SyntheticAuthority(scenario, truth, mode))
        assert receipt.execution is None and receipt.final.compatible_count == 6


def story_receipt():
    scenario, original, truth = fixture()
    authority = SyntheticAuthority(scenario, truth)
    receipt = run(scenario, original, authority, acquire=False)
    receipt = record_probe(receipt, "repeat_total")
    receipt = record_probe(receipt, "repeat_count")
    receipt = run(
        scenario,
        original,
        authority,
        prior=receipt,
        requested_action=EvidenceAction(kind="source", source=truth.links[0].source, cost=2),
    )
    receipt = record_probe(receipt, "repeat_total")
    return run(
        scenario,
        original,
        authority,
        prior=receipt,
        requested_action=EvidenceAction(kind="full_crosswalk", cost=2),
    )


def test_export_replays_the_interleaved_story_without_probe_authority():
    receipt = story_receipt()
    timeline = investigation_timeline(receipt)
    assert [r["request"] for r in timeline] == [
        "repeat_total",
        "repeat_count",
        "source",
        "repeat_total",
        "full_crosswalk",
    ]
    assert [r["compatible_after"] for r in timeline] == [6, 6, 2, 2, 1]
    assert len(receipt.observations) == len(receipt.steps) == 2
    assert len(receipt.investigations) == 3 and replay(export(receipt))
    restored = json.loads(export(receipt))["receipt"]
    assert restored["schema_version"] == "migration/3"
    assert restored["investigations"][0]["result"] == 100000
    assert receipt.execution.ownership_preserved


@pytest.mark.parametrize(
    "field,value",
    [
        ("result", 999),
        ("compatible_before", 1),
        ("compatible_after", 1),
        ("at_step", 8),
        ("information_gained", "ownership"),
        ("links", []),
    ],
)
def test_replay_rejects_forged_probe_information(field, value):
    bundle = json.loads(export(story_receipt()))
    bundle["receipt"]["investigations"][0][field] = value
    bundle["sha256"] = digest(bundle["receipt"])
    try:
        matched = replay(json.dumps(bundle))
    except ValueError:
        matched = False
    assert not matched


def test_existing_migration_artifacts_still_replay():
    root = Path(__file__).parents[1]
    for path in (root / "examples/migration").glob("*.json"):
        assert replay(path.read_text(encoding="utf-8")), path


def test_primary_journey_can_be_completed_from_main_content(monkeypatch):
    app = app_start(monkeypatch)
    assert any(b.label == "Inspect the proposal" for b in app.main.button)
    assert not any(b.label == "Inspect the proposal" for b in app.sidebar.button)
    predict(app)
    assert any(b.label == "Run this investigation" for b in app.main.button)
    investigate(app, "Check the total again")
    investigate(app, "Ask Owed to choose")
    assert any(b.label == "Verify the result" for b in app.main.button)
    click(app, "Verify the result")
    assert any("What Owed established" in h.value for h in app.subheader)
    click(app, "Replay this receipt offline")
    assert any("recorded results are semantically consistent" in c.value for c in app.caption)
    assert any("original temporary database" in c.value for c in app.caption)


def test_invalid_adapter_response_is_explained_without_repair(monkeypatch):
    class EmptyAuthority(SyntheticAuthority):
        def obtain(self, scope, action):
            return Observation(scope=scope, links=())

    monkeypatch.setattr("anomalon_workbench.migration_ui.SyntheticAuthority", EmptyAuthority)
    app = predict(app_start(monkeypatch))
    investigate(app, "Request the full identity mapping")
    assert any("Invalid identity response" in e.value for e in app.error)
    receipt = app.session_state["migration_receipt"]
    assert receipt.steps == () and receipt.observations == () and receipt.execution is None


def test_connection_information_is_not_removed_from_desktop_accessibility():
    css = stylesheet()
    desktop = re.search(r"\.an-rel\{([^}]*)\}", css)[1]
    assert "display:none" not in desktop and "clip-path:inset(50%)" in desktop
    markup = scene_html(
        [{"id": "a", "name": "Ava", "balance": "$1"}],
        [{"id": "b", "owner": "Owner not established", "balance": "$1"}],
        [{"source": "a", "destination": "b", "kind": "proposed"}],
        title="Proposal",
        caption="",
    )
    assert 'aria-label="Connections in text"' in markup
    assert "connections: Proposed: Ava to b" in markup


@pytest.mark.parametrize("size", [0, 1, 2])
def test_replay_applies_the_same_full_response_contract(monkeypatch, size):
    scenario, original, truth = fixture()

    class Incomplete:
        def obtain(self, scope, action):
            return Observation(scope=scope, links=truth.links[:size])

    # Construct a self-consistent receipt through the old permissive boundary.
    # The corrected replay must still reject its incomplete full response.
    with monkeypatch.context() as old_boundary:
        old_boundary.setattr(
            "anomalon_workbench.migration_demo.response_matches_action", lambda *args: True
        )
        legacy_bug = run(scenario, original, Incomplete(), one_action=True)
    assert not replay(export(legacy_bug))


def test_conflict_recovery_is_available_without_the_drawer(monkeypatch):
    app = app_start(monkeypatch)
    app.selectbox(key="migration_mode").set_value("contradictory").run()
    predict(app)
    investigate(app, "Ask Owed to choose")
    assert any(b.label == "Restart with consistent records" for b in app.main.button)
    click(app, "Restart with consistent records")
    assert app.session_state["migration_mode"] == "valid"
    assert "migration_receipt" not in app.session_state
    assert any(b.label == "Inspect the proposal" for b in app.main.button)


def test_probe_chronology_and_legacy_versions_cannot_be_rewritten():
    bundle = json.loads(export(story_receipt()))
    bundle["receipt"]["investigations"].reverse()
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(json.dumps(bundle))
    bundle = json.loads(export(story_receipt()))
    bundle["receipt"]["schema_version"] = bundle["receipt"]["checker"] = "migration/2"
    bundle["sha256"] = digest(bundle["receipt"])
    assert not replay(json.dumps(bundle))


@pytest.mark.parametrize("endpoint", ["source", "destination"])
def test_observed_mapping_cannot_refer_outside_the_rosters(endpoint):
    from anomalon_workbench.migration import Link

    scenario, original, truth = fixture()
    links = list(truth.links)
    links[0] = Link(
        source="unknown" if endpoint == "source" else links[0].source,
        destination="unknown" if endpoint == "destination" else links[0].destination,
    )
    response = Observation(scope=scenario.scope, links=tuple(links))
    assert evidence_status(scenario, response) == "invalid"
    assert not response_matches_action(
        scenario, EvidenceAction(kind="full_crosswalk", cost=2), response
    )
