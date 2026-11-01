"""Bind the deliverable files and reject accidental inclusion of configured secrets."""

import hashlib
import json
import os
from pathlib import Path

from anomalon_workbench.providers import load_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    load_environment(ROOT / ".env")
    paths = [
        ROOT / name
        for name in (
            "README.md",
            "LICENSE",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".gitignore",
            ".gitattributes",
            ".env.example",
            "app.py",
            "Dockerfile",
            ".dockerignore",
            "render.yaml",
            "proof_knowledge_obligations_mvp.md",
        )
    ]
    for directory in ("src", "tests", "scripts", "docs", "fixtures", "examples", "evidence", ".github"):
        paths.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.name != "release-manifest.json"
        )
    paths.extend(
        ROOT / "lean" / name for name in ("Ledger.lean", "Migration.lean", "lean-toolchain", "lakefile.toml")
    )
    secrets = [
        v.encode()
        for k, v in os.environ.items()
        if any(s in k.upper() for s in ("API_KEY", "TOKEN", "SECRET")) and len(v) >= 8
    ]
    files = {}
    for path in sorted(set(paths)):
        content = path.read_bytes()
        if any(secret in content for secret in secrets):
            raise RuntimeError(
                "Configured secret found in deliverable: " + str(path.relative_to(ROOT))
            )
        files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(content).hexdigest()
    report = {
        "version": "0.0.1.0",
        "display_name": "Owed — The Accountable Agent Workbench",
        "files_sha256": files,
        "scope": "File integrity and configured-secret scan; not a signature or authorship certificate",
    }
    (ROOT / "evidence/release-manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Release manifest: {len(files)} files; no configured secret values found.")


if __name__ == "__main__":
    main()
