from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_public_guided_migration_session_and_replay(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path))
    root = Path(__file__).parents[1]
    app = AppTest.from_file(str(root / "app.py"), default_timeout=20).run()
    assert not app.exception
    assert app.sidebar.radio[0].value == "Migration challenge"
    next(b for b in app.button if b.label == "Run the migration challenge").click().run()
    assert not app.exception
    receipt = app.session_state["migration_receipt"]
    assert receipt.steps == () and receipt.preview.total_preserved
    next(
        b for b in app.button if b.label == "Obtain selected evidence and apply justified repair"
    ).click().run()
    assert not app.exception
    receipt = app.session_state["migration_receipt"]
    assert receipt.execution.ownership_preserved
    next(b for b in app.button if b.label == "Replay this receipt offline").click().run()
    assert app.session_state["migration_replay"] is True
    other = AppTest.from_file(str(root / "app.py"), default_timeout=20).run()
    assert "migration_receipt" not in other.session_state
    next(b for b in app.button if b.label == "Change snapshot and crosswalk version").click().run()
    assert not app.exception
    assert any("remains history" in w.value for w in app.warning)
    assert app.session_state["migration_receipt"] == receipt
    assert not any(b.label == "Run with live model" for b in app.button)


def test_public_missing_stale_and_conflicting_modes(monkeypatch):
    monkeypatch.setenv("WORKBENCH_MODE", "hosted")
    monkeypatch.setenv("WORKBENCH_LIVE_ENABLED", "false")
    for mode in ("missing", "stale", "contradictory"):
        app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()
        app.selectbox[0].set_value(mode).run()
        next(b for b in app.button if b.label == "Run the migration challenge").click().run()
        next(b for b in app.button if b.label == "Obtain selected evidence and apply justified repair").click().run()
        assert not app.exception
        receipt = app.session_state["migration_receipt"]
        assert receipt.execution is None
        if mode == "stale":
            next(b for b in app.button if b.label == "Refresh stale crosswalk from current authority").click().run()
            assert not app.exception
            assert app.session_state["migration_receipt"].execution.ownership_preserved
