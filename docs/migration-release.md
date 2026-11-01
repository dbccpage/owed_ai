# Migration release and later custom domain

The release candidate changes the default journey and adds migration core modules,
CLI, independent row/witness checks, three Lean model theorems and source-bound
proof evidence. Existing labs and live-provider policy remain available. Live model
experiments stay **disabled**. The candidate has not been deployed.

## Build and local preview

```powershell
uv sync --locked
uv run pytest -q
uv run ruff check src tests scripts app.py
uv run mypy src
uv run python scripts/check_migration_lean.py
uv run python scripts/migration_validation.py
uv build
docker build -t owed:validation .
uv run python scripts/check_container.py
```

Start a local hosted preview with `WORKBENCH_MODE=hosted`,
`WORKBENCH_LIVE_ENABLED=false`, a writable `WORKBENCH_DATA_DIR`, and
`uv run python -m anomalon_workbench.serve`. The default local Streamlit command
in the README also runs the challenge. No provider key is needed for the challenge.

The Docker entrypoint and `/_stcore/health` endpoint are unchanged. The image now
includes `lean/Migration.lean` and `evidence/migration-lean.json`; source mismatch
displays **not verified for this build**, never a successful proof status. The
source archive must include those same artifacts. The current free service is
ephemeral: export is the retention mechanism. The paid Blueprint describes a
future persistent live-operator deployment and is not a description of the free
service's current resources.

## Authorized release checklist

1. Finish actual desktop/mobile journey review and the import adversarial audit.
2. Review the draft PR and bind the successful tests/container results to its head.
3. Inspect Render's service `owed-workbench` (`srv-dbj5eih42hec73c30q6g`), its
   repository/branch, current successful deploy, free compute and environment.
   Confirm `WORKBENCH_LIVE_ENABLED=false` and absence of deployment API keys.
4. When publication is authorized, manually deploy the reviewed SHA. Check health,
   all challenge stages, fault modes, receipt export/replay and proof artifact status
   at the actual hosted URL. Record cold start separately from warm-core timings.
5. Keep `https://owed-workbench.onrender.com/` usable throughout domain setup.

## Rollback

Use Render's Deploys page to roll back to the successful deployment of
`7d81005b0cffba6d30d9fa34c8aff4fe73ccd829` if that retained artifact is available.
Otherwise manually deploy that commit after checking service configuration. Verify
health and the earlier three-lab UI. Reconfirm live-off and credentials after the
rollback. Domain routing and persistent disk state do not roll back with code.
See [Render rollback behavior](https://render.com/docs/rollbacks).

## Later domain setup: owed.anomalon.com

This name matches Owed and is a proposed hostname, not a verified public URL.
No registration or paid-resource change is needed merely to propose a subdomain.

1. In the actual Render service Settings → Custom Domains, add `owed.anomalon.com`.
2. Read the DNS record Render supplies. At the authoritative DNS provider, create
   only that subdomain record with the displayed value; inspect existing records
   before changing anything. Preserve the apex and unrelated records. Do not use
   guessed addresses or alter nameservers.
3. Verify the domain in Render and wait for certificate issuance. Check authoritative
   DNS, HTTPS with certificate validation, `/_stcore/health`, the actual UI and replay.
4. Set `WORKBENCH_PUBLIC_URL` to the verified origin and update documentation using
   observed values. Keep live experiments off. Before any future authenticated live
   release, register the exact `/oauth2callback` URI and complete actual Google
   validation plus a dedicated provider-side spending cap.

The current [Render domain documentation](https://render.com/docs/custom-domains)
specifies add domain → configure provider DNS → verify in Render. A successful
DNS lookup alone is not proof of working HTTPS or application routing.
