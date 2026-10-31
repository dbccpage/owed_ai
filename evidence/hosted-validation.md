# Hosted MVP validation — October 31, 2026

The Render preparation adds a public demo, Google OIDC configuration, operator
isolation and shared application spending controls. This is preparation evidence;
no Render service or DNS record has been provisioned, and no production Google
client has been verified.
The operator explicitly deferred real Google validation until launch.

| Layer | Observed result |
|---|---|
| Windows Python suite | 65 tests pass, including 16 hosted authorization, isolation, spending and public-UI cases. |
| Static checks | Ruff passes. Strict mypy passes for 16 modules on Windows and with the Linux platform target. |
| Linux CI | 65 tests, Ruff and strict mypy passed on Ubuntu with Python 3.12. |
| Real container | Docker build, HTTP health, public inspector rendering, uid 10001 server execution and volume retention across restart all pass. |
| OIDC browser flow | A loopback provider issued signed RS256 identity tokens through the real Streamlit state/nonce/callback/cookie flow. Two allowlisted synthetic identities and one denied identity were exercised. This is not Google-account verification. |
| Authenticated live labs | Browser → scoped SQLite → separate worker → spending reservation → OpenRouter → persisted receipt. All three labs completed in 1 + 1 + 9 requests; all three replayed offline. |
| Revision | Parent 4/4, child 3/4: regression. Candidate not admitted. |
| Isolation | The second authorized identity saw no first-operator runs and zero usage. The denied identity had no live action even with the simulated actor set to operator. Tests also verify separate artifacts, cancellation and active prompt decisions. |
| Spending | 11 requests reported $0.0067204; integer-microdollar accounting charged $0.006724 after rounding each request upward. No uncertain costs in this live sample. Concurrent reservation tests, request caps, unknown-cost retention, revocation, and overrun halt tests pass. |
| Private data | Tenant databases and transcripts remain under ignored local data. The published hosted evidence contains summary metadata and screenshot observations only. |

The first container smoke test failed at startup. The privilege drop now sets the
application user's home directory; the smoke test also retains startup diagnostics
for its credential-free container. The corrected source at
`a7d49f9725fc06bec9d890a26b2bccf8b880901e` passed
[Linux and container validation](https://github.com/dbccpage/owed-ai/actions/runs/41238808431).
The earlier failing run remains visible in GitHub. Final PR checks independently
show the result for the latest branch head.

The first local OIDC attempt exposed an incorrect environment encoding for
`STREAMLIT_SECRETS_FILES`. It now receives the filename directly. The subsequent
browser flow succeeded. A missing login-status claim fails closed instead of
crashing the public view. The synthetic identity provider was stopped after testing;
the local preview was restarted with live access disabled.

`hosted-live.json` records receipt digests, exact request counts and accounting.
`hosted-revision.jpg`, `hosted-isolation.jpg` and `hosted-denied.jpg` record browser
observations using synthetic identities. Existing curated baseline replays remain
separate from private hosted runs. A real Google callback, deployment-key credit
limit, Render provisioning, and `workbench.anomalon.com` DNS/TLS are launch gates
described in [the deployment guide](../docs/deployment.md).

Application reservation limits are not guaranteed provider billing limits. Unknown
charges remain reserved, and an overrun stops future calls but cannot reverse an
in-flight charge. Configure a dedicated provider-side key limit before live launch.
This validation is not a penetration test or a claim of multi-instance readiness.
