# Owed — The Accountable Agent Workbench

v0.0.1.0 · from Anomalon / Omega Engine · [dbccpage/owed_ai](https://github.com/dbccpage/owed_ai)

## Migration challenge — live public demo

**The total was right. The balances went to the wrong accounts.**

Run a synthetic customer-account migration, inspect why its passing total and row
checks leave ownership unresolved, obtain the missing correspondence, and inspect
an actually committed SQLite repair. The default public and local page follows this journey;
the original research labs remain available in the sidebar.

The current public deployment is **[owed.anomalon.com](https://owed.anomalon.com/)**
([Render fallback](https://owed-workbench.onrender.com/)).
PR #4 is merged, and the migration challenge was deployed from `86c2d90`.
**Live model experiments remain disabled.** On November 1, 2026, normal Chrome
validation through this hostname passed preview, witness verification, accepted
evidence, committed repair, export, browser/CLI replay, receipt import checks and
snapshot invalidation. Hosted missing/stale/conflicting evidence checks, stale
refresh, case generation and session reset also pass. See the
[deployment evidence](evidence/migration-deployment.json)
for exact scope and deferred live-launch gates, and the [review record](evidence/migration-pr-review.json)
for the 274-test, typing, lint, container and Lean validation results.

```powershell
uv sync --locked
uv run streamlit run app.py --server.address 127.0.0.1
uv run owed-migration --seed 0 --output migration.json
uv run owed-migration --replay migration.json
uv run python scripts/check_migration_lean.py
```

The public challenge needs no model provider or login. It supports 2–6 accounts,
signed integer USD cents and bijective identity correspondence into a fresh
destination. Preview and repair execute in separate temporary databases. Export
receipts for history; session reset and service restarts do not provide durability.
The public operator role is a simulation scoped to synthetic data.

See the [acceptance report](docs/migration-acceptance.md) and
[migration walkthrough](docs/migration-walkthrough.md). Three model results are
checked in Lean 4.19.0; runtime database conformance is checked separately. Hashes
bind receipt content, not the truth of the synthetic authority or authorship of a
self-consistently rewritten bundle.

**What did the agent establish—and what does it still owe?**

A small Python workbench distilling Anomalon/Omega Engine research into three inspectable experiments. Live models propose. Exact checkers decide what the represented evidence supports. Human operators retain admission authority.

| Experiment | What you can observe |
|---|---|
| Evidence | A valid total leaves individual reserves underdetermined; new observations resolve the claim. |
| Composition | Every pair of constraints works, but the whole set contradicts; a cycle witnesses the obstruction. |
| Revision | One prompt becomes a candidate child; development feedback, withheld evaluation, ancestry, and admission stay separate. |

## Start locally

Requires Python **3.12** and [uv](https://docs.astral.sh/uv/). All authored application code is Python. Streamlit and other dependencies contain their own browser/native components.

```powershell
git clone https://github.com/dbccpage/owed_ai.git
cd owed_ai
uv sync --locked
Copy-Item .env.example .env  # Only when you do not already have .env
uv run streamlit run app.py --server.address 127.0.0.1
```

The first two labs have exact, editable host checks without credentials. For live generation, enter a provider and explicit model ID in the sidebar and configure its key in `.env`. Native `json_schema` mode is recommended for supported models; use `json_prompt` for servers without native support. Invalid output remains a visible failure in both modes. No model is downloaded automatically.

| Provider | Credential | Default base URL |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1` |
| `openrouter` | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |
| `compatible` | Variable named by `WORKBENCH_KEY_ENV` (default `COMPATIBLE_API_KEY`) | `https://api.openai.com/v1` |
| `local` | Optional `LOCAL_API_KEY` | `http://localhost:11434/v1` |

For an OpenAI-compatible server, set `WORKBENCH_BASE_URL` to its `/v1` endpoint and explicitly select the credential variable. To use `OPENAI_API_KEY`, set `WORKBENCH_KEY_ENV=OPENAI_API_KEY`. Existing process variables override `.env`. Hosted URLs require HTTPS; plain HTTP is permitted only for loopback. Choose `local` for an already-running local server, including its model ID.

Example nonsecret configuration:

```dotenv
WORKBENCH_PROVIDER=anthropic
WORKBENCH_MODEL=claude-haiku-4-5-20251001
WORKBENCH_OUTPUT_MODE=json_schema
```

That model was available during the recorded validation; availability can change. Credentials never belong in examples, receipts, or Git. `.env` and local `data/` are ignored. The application never creates a key or changes your `.env`.

## Reproduce a result

For a public demo with Google-authenticated live experiments, see the
[Render deployment guide](docs/deployment.md). The Blueprint starts with live access
disabled. Hosted operators receive isolated stores and share transactional request
and spending controls. [owed.anomalon.com](https://owed.anomalon.com/) is the public product address;
`anomalon.com` remains the future home of the broader Omega Engine programme.
`WORKBENCH_AUTH_ENABLED=true` permits Google sign-in validation while
`WORKBENCH_LIVE_ENABLED=false` continues to block all live model experiments.

```powershell
uv run anomalon check ledger
uv run anomalon check graph
uv run anomalon run ledger --provider anthropic --model claude-haiku-4-5-20251001 --wait
uv run anomalon run revision --provider anthropic --model claude-haiku-4-5-20251001 --wait
uv run anomalon list
uv run anomalon show RUN_ID
uv run anomalon review RUN_ID
uv run anomalon export RUN_ID replay.json
uv run anomalon replay replay.json
uv run anomalon admit RUN_ID --actor operator
```

`run ... --input file.json` accepts the same bounded input records edited in the UI. A revision input may contain a `parent` prompt record. With no input, the latest explicitly admitted prompt is used. CLI admission is a **local simulated role decision**. Hosted UI admission additionally requires an authorized login and applies only to that operator's workspace. It is not automatic, including on a tie or perfect score.

Use `cancel RUN_ID` to stop new requests; an in-flight call may finish before cancellation is observed. A worker watchdog enforces the total deadline. `recover` marks abandoned jobs interrupted after their deadline and grace interval, without resubmitting uncertain requests. SQLite admits one active run, and duplicate worker launches cannot claim it twice.

Default limits: 12 requests, 300 seconds, 2,048 output tokens per request. Usage is recorded when reported by the provider. Missing token/cost information is unknown, never a zero-cost claim. These are request/time/token limits, not a dollar cap.

## How the implementation earns trust

- A pure finite ledger checker enumerates 121 states. A separate implementation checks counts and witnesses; an empty compatible set is inconsistent, never vacuous support.
- Graph reconstruction uses exact rational arithmetic. Its independent certificate verifier checks all potential equations or the continuity and residual of an obstruction cycle. Each disconnected component has its own gauge.
- Models return schema-validated data. They cannot execute generated code, insert accepted observations, change policy, or authorize actions. Graph repairs touch explicitly editable synthetic edges only.
- The revision experiment makes nine calls: two parent development answers, one mutation, two child development answers, and four parent/child withheld answers. The child freezes before withheld evaluation. Evaluation grades exact verdicts on four cases; it does **not** certify every sentence in an explanation or broad model reliability.
- Receipts bind inputs, prompts, responses, model configuration, checker/policy versions and semantic outputs. Timing is outside semantic receipts. Offline replay checks the recorded proposals again; it does not reproduce fresh model sampling.
- Source/build metadata and SHA-256 detect changes relative to a supplied receipt. They do not establish observation truth, authorship, or protection from a local user replacing both content and its receipt.

## Validate

```powershell
uv run pytest -q
uv run ruff check src tests scripts app.py
uv run mypy src
uv run python scripts/check_lean.py
uv run python scripts/compare_fixtures.py
```

To validate all three labs through a live provider and the real worker, set `WORKBENCH_OUTPUT_MODE=json_schema` for a supported model, then run:

```powershell
uv run python scripts/live_validation.py --provider openrouter --model openai/gpt-4.1-mini
```

Every attempt is retained under `examples/attempts/`; incomplete validation returns a nonzero exit code. OpenRouter completed all three labs with `openai/gpt-4.1-mini`: 11 requests, three matching offline replays, and a 3/4–3/4 revision tie with no admission. Earlier authentication and strict-schema failures are preserved in the [evidence report](evidence/README.md). After replacing a key in `.env`, restart an already-running Streamlit process so its previously loaded environment does not retain the old credential.

Lean is optional for operating the application. The supplement pins Lean 4.19.0 and imports only `Std`, with no Mathlib. The audit checks four named statements and rejects undeclared axioms, including `sorryAx`. A recorded check in `evidence/lean-verification.json` is distinct from a fresh local check and from each Python run's `proof_status=not_checked`.

On restricted Windows runners, pytest may need a writable `--basetemp`; Streamlit tests also need permission to create a local asyncio socket pair. These are environment requirements, not reasons to skip assertions.

See [validation evidence](evidence/README.md), the [five-minute tour](docs/walkthrough.md), [architecture](docs/architecture.md), and [research crosswalk](docs/source-crosswalk.md). The original [experiment proposal](proof_knowledge_obligations_mvp.md) is preserved.

This is a research MVP with local operation and an optional single-instance hosted mode. Its finite results do not establish general epistemic completeness, audited production security, universal LGGR claims, or autonomous scientific discovery. No GitHub remote or deployment is required for local use.

The first [Cognitive Optimization slice](docs/cognitive-optimization.md) pairs a short question/result/next-check presentation with a deterministic audit of structured proposal/evidence mismatches. It leaves original receipts unchanged and treats human-comprehension benefits as hypotheses to test.
