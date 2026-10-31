import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from anomalon_workbench.domain import RunSpec, json_object
from anomalon_workbench.examples import ledger_example
from anomalon_workbench.providers import ProviderConfig
from anomalon_workbench.service import replay
from anomalon_workbench.storage import Store
from anomalon_workbench.worker import launch


def test_separate_worker_duplicate_launch_and_cancel(tmp_path):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.rfile.read(int(self.headers["Content-Length"])))
            payload = json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "interpretation": "Test server response, not a live model.",
                                        "verdict": "underdetermined",
                                        "evidence_requests": [],
                                        "repairs": [],
                                    }
                                )
                            },
                            "finish_reason": "stop",
                        }
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    children = []
    try:
        store = Store(tmp_path)
        config = ProviderConfig(
            "local", "test-http-server", f"http://127.0.0.1:{server.server_port}/v1"
        )
        spec = RunSpec(lab="ledger", payload=json_object(ledger_example()))
        run_id = store.enqueue("first", json_object(spec), config.public())
        children = [launch(store, run_id), launch(store, run_id)]
        for child in children:
            child.wait(timeout=20)
        assert len(requests) == 1
        row = store.get(run_id)
        assert row["status"] == "completed"
        assert replay(store.read(row["receipt_hash"]))
        cancelled = store.enqueue("second", json_object(spec), config.public())
        store.cancel(cancelled)
        child = launch(store, cancelled)
        children.append(child)
        child.wait(timeout=10)
        assert len(requests) == 1
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
