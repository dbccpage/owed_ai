"""Render entrypoint. Authentication secrets exist only in a private runtime file."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .hosting import HostedPolicy, data_root, hosted_mode, secure_url
from .providers import load_environment


def auth_document() -> str:
    public_url = os.environ["WORKBENCH_PUBLIC_URL"].rstrip("/")
    metadata = os.getenv(
        "WORKBENCH_AUTH_METADATA_URL",
        "https://accounts.google.com/.well-known/openid-configuration",
    )
    if not secure_url(public_url) or urlsplit(public_url).path or not secure_url(metadata):
        raise ValueError("invalid_auth_urls")
    values = {
        "redirect_uri": public_url + "/oauth2callback",
        "cookie_secret": os.environ["WORKBENCH_COOKIE_SECRET"],
        "client_id": os.environ["WORKBENCH_AUTH_CLIENT_ID"],
        "client_secret": os.environ["WORKBENCH_AUTH_CLIENT_SECRET"],
        "server_metadata_url": metadata,
    }
    if any(not value.strip() for value in values.values()) or len(values["cookie_secret"]) < 32:
        raise ValueError("missing_auth_secrets")
    # JSON string quoting is valid TOML basic-string quoting for these ASCII settings.
    return "[auth]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in values.items()) + "\n"


def main() -> None:
    load_environment()
    if sys.platform != "win32" and os.getenv("WORKBENCH_CONTAINER") == "true":
        import pwd

        if os.geteuid() == 0:
            root = data_root()
            if root != Path("/var/data/owed"):
                raise ValueError("unexpected_container_storage_path")
            root.mkdir(parents=True, exist_ok=True)
            account = pwd.getpwnam("owed")
            os.chown(root, account.pw_uid, account.pw_gid)
            os.setgroups([])
            os.setgid(account.pw_gid)
            os.setuid(account.pw_uid)
            os.environ["HOME"] = account.pw_dir
    os.environ.setdefault("WORKBENCH_MODE", "hosted")
    if not hosted_mode():
        raise ValueError("serve_requires_hosted_mode")
    policy = HostedPolicy.from_env()
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=root):
        pass  # Fail at startup if the mounted data directory is not writable.
    if policy.auth_enabled:
        document = auth_document()
        # Never build credentials into an image or write them into the mounted run archive.
        descriptor, filename = tempfile.mkstemp(prefix="owed-auth-", suffix=".toml")
        os.chmod(filename, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(document)
        os.environ["STREAMLIT_SECRETS_FILES"] = filename
    from streamlit.web import cli

    sys.argv = [
        "streamlit", "run", str(Path("app.py").resolve()),
        "--server.address=" + os.getenv("WORKBENCH_BIND_ADDRESS", "0.0.0.0"),
        "--server.port=" + os.getenv("PORT", "8501"),
        "--server.headless=true", "--browser.gatherUsageStats=false",
        "--server.enableCORS=true", "--server.enableXsrfProtection=true",
        "--server.enableStaticServing=false", "--server.maxUploadSize=1",
        "--client.showErrorDetails=false",
    ]
    cli.main()


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError):
        raise SystemExit("Invalid hosted configuration; check the deployment guide. No secrets logged.") from None
