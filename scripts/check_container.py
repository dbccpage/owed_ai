"""Exercise the real image without credentials, on a fresh persistent Docker volume."""

import json
import subprocess
import time
import urllib.request
import uuid


def command(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def main():
    name = "owed-check-" + uuid.uuid4().hex[:8]
    command("volume", "create", name)
    try:
        command("run", "-d", "--name", name, "-p", "127.0.0.1::8501",
                "-v", name + ":/var/data", "owed:validation")
        port = command("port", name, "8501/tcp").split(":")[-1]
        url = "http://127.0.0.1:" + port + "/_stcore/health"
        for _ in range(60):
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("container_health_failed")
        # PID 1's effective uid must be the unprivileged application user.
        status = command("exec", name, "cat", "/proc/1/status")
        uid = next(line for line in status.splitlines() if line.startswith("Uid:"))
        assert set(uid.split()[1:]) == {"10001"}
        command("exec", "--user", "10001", name, "/app/.venv/bin/python", "-c",
                "from streamlit.testing.v1 import AppTest; "
                "a=AppTest.from_file('/app/app.py').run(); assert not a.exception; "
                "a.sidebar.radio[0].set_value('Run inspector').run(); assert not a.exception; "
                "assert not any(s.label=='Run' for s in a.selectbox)")
        migration_check = """
from pathlib import Path
from streamlit.testing.v1 import AppTest
from anomalon_workbench.migration_demo import export, investigation_timeline, replay
from anomalon_workbench.migration_proof import proof_status
before = set(Path('/tmp').glob('owed-migration-*'))
assert proof_status()['status'] == 'verified_during_build'
app = AppTest.from_file('/app/app.py', default_timeout=20).run()
app = app.sidebar.radio[0].set_value('Migration challenge').run()
assert not app.exception
next(b for b in app.main.button if b.label == 'Inspect the proposal').click().run()
assert not app.exception
assert app.session_state['migration_receipt'].initial.ownership == 'underdetermined'
next(b for b in app.main.button if b.label == 'Make your prediction').click().run()
app.main.radio(key='migration_prediction').set_value('Not enough information').run()
next(b for b in app.main.button if b.label == 'Test my prediction').click().run()
assert app.session_state['migration_receipt'].steps == ()
assert any('Possible assignment A' in m.value for m in app.markdown)
assert not any(b.label == 'Run this investigation' for b in app.sidebar.button)
app.main.selectbox(key='migration_investigation').set_value('Check the total again').run()
next(b for b in app.main.button if b.label == 'Run this investigation').click().run()
assert len(app.session_state['migration_receipt'].investigations) == 1
assert app.session_state['migration_receipt'].observations == ()
app.main.selectbox(key='migration_investigation').set_value('Ask Owed to choose').run()
next(b for b in app.main.button if b.label == 'Run this investigation').click().run()
next(b for b in app.main.button if b.label == 'Verify the result').click().run()
assert not app.exception
receipt = app.session_state['migration_receipt']
assert receipt.execution.ownership_preserved and receipt.execution.identity_coverage
assert replay(export(receipt))
assert investigation_timeline(receipt)[0]['compatible_after'] == 6
assert not any(b.label == 'Run with live model' for b in app.button)
assert set(Path('/tmp').glob('owed-migration-*')) == before
"""
        command("exec", "--user", "10001", name, "/app/.venv/bin/python", "-c", migration_check)
        command("exec", "--user", "10001", name, "/app/.venv/bin/python", "-c",
                "from pathlib import Path; Path('/var/data/owed/persistence-check').write_text('retained')")
        command("restart", name)
        assert command("exec", "--user", "10001", name, "cat",
                       "/var/data/owed/persistence-check") == "retained"
        print(json.dumps({"health": True, "public_ui": True, "migration_journey": True,
                          "migration_proof_sources": True, "temporary_cleanup": True,
                          "unprivileged_server": True, "persistent_volume": True,
                          "scope": "Real Docker image, public mode, no provider credentials"}))
    except Exception:
        print(command("logs", name))  # This test container receives no real credentials.
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
        subprocess.run(["docker", "volume", "rm", name], check=False, capture_output=True)


if __name__ == "__main__":
    main()
