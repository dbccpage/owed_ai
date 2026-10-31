"""Loopback-only OIDC integration fixture. Never deploy or use as real authentication.

Exercises Streamlit's actual state/nonce, signed ID-token and cookie flow. Identities
are synthetic and selected on the fixture page; this does not verify Google login.
"""

import argparse
import base64
import html
import json
import os
import secrets
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from joserfc import jwt
from joserfc.jwk import RSAKey

from anomalon_workbench.providers import load_environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-port", type=int, default=8502)
    parser.add_argument("--idp-port", type=int, default=8765)
    parser.add_argument("--live-provider", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root / "data" / "oidc-validation"
    folder.mkdir(parents=True, exist_ok=True)
    issuer = f"http://127.0.0.1:{args.idp_port}"
    public = f"http://127.0.0.1:{args.app_port}"
    key = RSAKey.generate_key(2048)
    public_key = key.as_dict(private=False)
    public_key.update({"kid": "fixture", "use": "sig", "alg": "RS256"})
    client_secret = secrets.token_urlsafe(32)
    pending, codes = {}, {}

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, body, status=200):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            url = urlsplit(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/.well-known/openid-configuration":
                self.send_json({
                    "issuer": issuer, "authorization_endpoint": issuer + "/authorize",
                    "token_endpoint": issuer + "/token", "jwks_uri": issuer + "/jwks",
                    "response_types_supported": ["code"], "subject_types_supported": ["public"],
                    "id_token_signing_alg_values_supported": ["RS256"],
                    "token_endpoint_auth_methods_supported": ["client_secret_basic"],
                })
            elif url.path == "/jwks":
                self.send_json({"keys": [public_key]})
            elif url.path == "/authorize":
                if query.get("redirect_uri") != public + "/oauth2callback" or query.get("client_id") != "owed-fixture":
                    self.send_json({"error": "invalid_fixture_client"}, 400)
                    return
                identifier = secrets.token_urlsafe(24)
                pending[identifier] = query
                links = "".join(
                    f'<p><a href="/approve?{html.escape(urlencode({"id": identifier, "subject": subject}))}">'
                    f'Sign in as fixture {subject}</a></p>' for subject in ("alice", "bob", "outsider")
                )
                raw = ("<h1>Local OIDC test fixture</h1><p>Synthetic identities, not Google authentication.</p>" + links).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif url.path == "/approve" and query.get("subject") in ("alice", "bob", "outsider"):
                auth = pending.pop(query.get("id"), None)
                if not auth:
                    self.send_json({"error": "invalid_fixture_session"}, 400)
                    return
                code = secrets.token_urlsafe(24)
                codes[code] = (query["subject"], auth.get("nonce"))
                self.send_response(302)
                self.send_header("Location", public + "/oauth2callback?" + urlencode({"code": code, "state": auth["state"]}))
                self.end_headers()
            else:
                self.send_json({"error": "not_found"}, 404)

        def do_POST(self):
            expected = "Basic " + base64.b64encode(("owed-fixture:" + client_secret).encode()).decode()
            if self.path != "/token" or self.headers.get("Authorization") != expected:
                self.send_json({"error": "invalid_client"}, 401)
                return
            query = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            record = codes.pop(query.get("code", [""])[0], None)
            if not record:
                self.send_json({"error": "invalid_grant"}, 400)
                return
            subject, nonce = record
            now = int(time.time())
            token = jwt.encode({"alg": "RS256", "kid": "fixture"}, {
                "iss": issuer, "aud": "owed-fixture", "sub": subject, "iat": now,
                "exp": now + 3600, "nonce": nonce, "name": "Fixture " + subject,
            }, key)
            self.send_json({"access_token": "fixture-unused", "token_type": "Bearer", "id_token": token})

        def log_message(self, *unused):
            pass  # Never log callback codes, cookies or tokens.

    if args.live_provider:
        load_environment(root / ".env")
    env = dict(os.environ)
    env.pop("RENDER", None)
    if not args.live_provider:
        env["OPENROUTER_API_KEY"] = ""
    env.update({
        "WORKBENCH_MODE": "hosted", "WORKBENCH_LIVE_ENABLED": "true",
        "WORKBENCH_AUTH_ISSUER": issuer, "WORKBENCH_AUTH_METADATA_URL": issuer + "/.well-known/openid-configuration",
        "WORKBENCH_PUBLIC_URL": public, "WORKBENCH_AUTH_CLIENT_ID": "owed-fixture",
        "WORKBENCH_AUTH_CLIENT_SECRET": client_secret, "WORKBENCH_COOKIE_SECRET": secrets.token_urlsafe(48),
        "WORKBENCH_ALLOWED_SUBJECTS": '["alice","bob"]',
        "WORKBENCH_DATA_DIR": str(folder / "runs"), "PORT": str(args.app_port),
        "AUTHLIB_INSECURE_TRANSPORT": "1",
        "WORKBENCH_BIND_ADDRESS": "127.0.0.1",
    })
    server = ThreadingHTTPServer(("127.0.0.1", args.idp_port), Handler)
    with (folder / "server.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen([sys.executable, "-m", "anomalon_workbench.serve"], cwd=root, env=env, stdout=log, stderr=log)
        print("Local fixture app: " + public, flush=True)
        try:
            server.serve_forever()
        finally:
            child.terminate()
            child.wait(timeout=10)
            server.server_close()


if __name__ == "__main__":
    main()
