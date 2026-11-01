# Render deployment and the Anomalon home

Current public endpoint: [owed.anomalon.com](https://owed.anomalon.com/), with
[the Render endpoint](https://owed-workbench.onrender.com/) retained as a fallback.
The public-only service uses free compute and ephemeral state; live model execution
is disabled. The paid persistent Blueprint below is a separate future configuration.
The migration challenge is deployed from merged PR #4, commit `86c2d90`.
See the [migration release record](migration-release.md) and
[hosted validation evidence](../evidence/migration-deployment.json) for the actual
browser journey, receipt replay and remaining checks. The owner completed the
domain connection; CNAME and certificate-validated HTTPS health/app-shell checks
passed on November 1, 2026. Live model experiments remain disabled; Google login
and a dedicated provider-side spending cap remain future live-launch gates.

Use **owed.anomalon.com** for Owed. Reserve **anomalon.com** for the wider
Anomalon story and the future Omega Engine V1.0RC product home. The apex can later
link Pre-Genesis, Genesis, quantum mechanics, the engine, research repositories,
and individual products. This release does not claim to implement that full estate.
No DNS records or hosting services are changed by this repository.

## Runtime and boundaries

`render.yaml` prepares one paid Docker web service, one 1 GB persistent disk,
manual deploys, health checks, and a public demo with live execution **off**.
The Python entrypoint initializes only `/var/data/owed` on the mounted disk and
drops to uid 10001 before serving requests. Streamlit and bounded worker subprocesses
share that filesystem. Keep **one service instance**: this is not a distributed queue.
Disk-backed deploys can interrupt runs; recovery never retries uncertain API calls.

Public visitors can explore finite checks and six curated recorded demonstrations.
They cannot enqueue models, enumerate private runs, upload replay programs, cancel
other people's work, or activate prompts. Login uses Streamlit's OIDC implementation;
the application separately requires the configured issuer, an allowlisted `sub`,
and an unexpired identity token. Email addresses are not used as identity keys.

Each operator gets `users/<SHA256(issuer,sub)>/` with separate SQLite, artifacts,
decisions, and active prompts. Raw identity claims do not enter model requests or
semantic receipts. Inspector refreshes recheck the current identity; workers recheck
their owner, scoped directory, fixed provider, expiry, allowlist, and run limits.
An authenticated operator can admit only eligible candidates in their own workspace.
The ledger's viewer/operator toggle remains a mathematical simulation.

## Google and Render setup

1. Review the paid service and disk configuration in `render.yaml`, then create a
   Render Blueprint from the reviewed branch. Leave `WORKBENCH_LIVE_ENABLED=false`
   for the first public deploy. Configure service billing in Render separately.
2. Add `owed.anomalon.com` as a Render custom domain. Use the exact DNS target
   Render supplies; do not point the apex domain away from its future home.
3. Create a Google OAuth **Web application** client, configure the consent audience
   and test users as appropriate, and register the exact authorized redirect URI:
   `https://owed.anomalon.com/oauth2callback`. If testing on Render's temporary
   hostname, register that callback too and set `WORKBENCH_PUBLIC_URL` to that origin.
4. Set `WORKBENCH_AUTH_CLIENT_ID` and `WORKBENCH_AUTH_CLIENT_SECRET` in Render's secret
   environment settings. The Blueprint generates `WORKBENCH_COOKIE_SECRET`; retain
   it across restarts. Do not commit any of these values. The entrypoint writes the
   OIDC TOML to an owner-only temporary file, outside the image and run archive.
5. Set `OPENROUTER_API_KEY` to a **dedicated, provider-limited deployment key**.
   Configure its credit limit/reset in OpenRouter; the application never modifies
   keys or account settings. Keep personal development keys out of this deployment.
6. Set `WORKBENCH_AUTH_ENABLED=true`, leave `WORKBENCH_LIVE_ENABLED=false`, and redeploy.
   This enables Google login/logout and identity inspection while every live model
   submission remains denied. The verified account-identifier expander shows only
   that user's own subject ID. Check sign-in, issuer/expiry validation and logout
   through the exact public callback; never copy tokens or client secrets into evidence.
7. Verify the dedicated OpenRouter key's provider-side credit limit and reset period.
   Only after both Google login and that cap are verified should live launch be
   considered. Set `WORKBENCH_ALLOWED_SUBJECTS` to a JSON list of approved subject IDs
   after checking operator identities; an empty list denies all operators. Enabling
   login alone never creates a private workspace or grants model authority. Keep
   `WORKBENCH_LIVE_ENABLED=false` until live launch is authorized.

The authentication switch defaults to the live switch when absent, preserving
existing live deployments. Set both explicitly in new deployments. A live-enabled,
auth-disabled configuration is rejected at startup. Real Google account validation
remains separate from the loopback OIDC fixture.

Logout clears the current Streamlit session and its browser identity cookie. Existing
tabs can retain their previously authenticated session until token expiry; it is not
a global Google-session revocation mechanism. Removing a subject from the server
allowlist and redeploying revokes access across application processes.

The server model is `openai/gpt-4.1-mini`, native schema mode, through OpenRouter's
fixed HTTPS endpoint. Hosted visitors cannot override credentials, URLs, provider,
model, or output mode. Local CLI/provider flexibility remains available in local mode.

## Spending controls

All operators share `control/spending.sqlite3`. A SQLite immediate transaction reserves
funds **before every model call**, across processes. Defaults are:

| Setting | Default |
|---|---|
| Global daily requests | 120 |
| Per-operator daily requests | 24 |
| Global daily application budget | $2.00 |
| Per-operator daily application budget | $0.50 |
| Reservation per request | $0.10 |
| Concurrent runs across operators | 1 |
| Each run | 12 requests, 300 seconds, 2,048 output tokens/request |

Dollar settings use integer microdollars: 1,000,000 equals $1. UTC dates define daily
windows. These are conservative **application reservations**, not token-price quotes
or a guarantee of the provider's final bill. Reported costs settle reservations with
upward rounding. Missing usage, timeouts, failures and process death retain the full
reservation. A reported cost above its reservation halts subsequent requests globally.
An in-flight call cannot be undone; use the provider-side key limit as a second control.
Changing the model requires reviewing the reservation against its prices and maximum
input/output size. Unknown cost never becomes zero.

The global request count includes uncertain submissions. There is no automatic retry
or provider fallback. Concurrency leases expire after the run deadline plus a grace
period; terminal workers release them. Set `WORKBENCH_LIVE_ENABLED=false` and redeploy
to disable new live activity. Inspect overrun evidence before an administrator resets
the `circuit` table; there is deliberately no visitor-accessible reset/refund control.
Do not erase the control database to recover capacity or restore it separately from
private run data. Back up the entire mounted directory with SQLite-consistent backups.

## Validation before public live launch

Run `uv sync --locked`, pytest, Ruff and strict mypy. The GitHub workflow also builds
the actual image and verifies its health, unprivileged server and mounted-volume
persistence across a restart. It makes no paid API requests and receives no secrets.

For local OIDC integration testing, run
`uv run python scripts/oidc_fixture.py` and open `http://127.0.0.1:8502`.
This loopback fixture uses signed tokens, state/nonce and the actual Streamlit cookie
flow, with clearly labeled synthetic identities. `--live-provider` explicitly enables
the configured local OpenRouter key for bounded end-to-end worker tests. The fixture
is excluded from the production image and must never be hosted as authentication.

Before production launch verify Google login and logout, an unauthorized account,
two isolated operators, all three live labs, caps under concurrency, restart recovery,
and receipt replay. Inspect the container/DNS/TLS/Google results separately from the
local fixture results. Review deployment costs before provisioning; no deployment is
performed by running tests or opening a PR.

Primary references: [Streamlit OIDC](https://docs.streamlit.io/develop/concepts/connections/authentication),
[Render disks](https://render.com/docs/disks),
[Render Blueprint fields](https://render.com/docs/blueprint-spec),
[OpenRouter key credit limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-keys).
