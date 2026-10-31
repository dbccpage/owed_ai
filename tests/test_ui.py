import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from anomalon_workbench.storage import Store


def test_ui_pages_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
    assert not app.exception
    for page in ["Evidence", "Composition", "Revision", "Run inspector", "Overview"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
    app.sidebar.radio[0].set_value("Evidence").run()
    app.selectbox[0].set_value("B = 20").run()
    assert not app.exception
    assert any("Supported" in h.value for h in app.subheader)


def test_replay_result_survives_rerender_without_submitting(tmp_path, monkeypatch):
    root = Path(__file__).parents[1]
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path))
    receipt = json.loads(
        (root / "examples/live/openrouter/revision.json").read_text(encoding="utf-8")
    )["receipt"]
    store = Store(tmp_path)
    run_id = store.enqueue("recorded-ui-test", receipt["spec"], {})
    assert store.claim(run_id, 1)
    store.finish(run_id, "completed", receipt)
    app = AppTest.from_file(str(root / "app.py"), default_timeout=15).run()
    app.sidebar.radio[0].set_value("Run inspector").run()
    assert any("reported cost: $0.005302 USD" in c.value for c in app.caption)
    next(b for b in app.button if b.label == "Verify offline replay").click().run()
    assert not app.exception
    assert any("Semantic replay matched:" in m.value and "True" in m.value for m in app.markdown)
    app.run()
    assert any("Semantic replay matched:" in m.value and "True" in m.value for m in app.markdown)
    assert len(store.list_runs()) == 1
    assert store.read(str(store.get(run_id)["receipt_hash"])) == receipt
