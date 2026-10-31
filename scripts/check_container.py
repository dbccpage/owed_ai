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
                "from pathlib import Path; Path('/var/data/owed/persistence-check').write_text('retained')")
        command("restart", name)
        assert command("exec", "--user", "10001", name, "cat",
                       "/var/data/owed/persistence-check") == "retained"
        print(json.dumps({"health": True, "unprivileged_server": True, "persistent_volume": True,
                          "scope": "Real Docker image, public mode, no provider credentials"}))
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
        subprocess.run(["docker", "volume", "rm", name], check=False, capture_output=True)


if __name__ == "__main__":
    main()
