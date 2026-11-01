# Migration challenge acceptance map

Implementation starts from `7d81005` (existing three-lab MVP). No migration code
exists at that baseline. Existing records, canonical hashing, strict JSON parser,
provider boundary and hosted live-off policy are reusable. Existing labs remain
secondary material. Target product hostname: **owed.anomalon.com**; this is a
proposal, not a verified DNS/TLS endpoint.

| ID | Requirement | Baseline | Acceptance evidence required |
|---|---|---|---|
| M01 | Real atomic preview and repaired SQLite execution | Missing | Actual rows, rollback, duplicate rerun tests |
| M02 | Independently checked ownership ambiguity | Missing | Two bijections, same observations, different assignment |
| M03 | Explicit evidence adapter and finite action selection | Missing | No hidden crosswalk in evaluator; informative actions and scope tests |
| M04 | Valid, missing, stale, contradictory observations | Ledger pattern only | Migration-specific verdict and provenance tests |
| M05 | Exact admission binds candidate/scope/evidence | Local role simulation only | Mutation denial; historical receipt preserved |
| M06 | Bounded receipt export and offline reevaluation | Existing lab replay only | Tamper detection; replay without authority query or execution |
| M07 | Generated cases and execution observer | Missing | At least 100 seeds, equal/negative balances, varied IDs/order |
| M08 | Three mandatory Lean results and axiom audit | Ledger proofs only | Actual pinned Lean check and source-bound artifact |
| M09 | Default guided public UI and session isolation | Three labs default | Fresh-session journey, reset, export/replay, mobile/desktop |
| M10 | CLI, examples, timings, walkthrough, release | Existing lab commands only | Repaired/unresolved/conflicting bundles; acceptance report |

The preceding interrupted domain turns made no authoritative changes. This goal
starts with source inspection and an executable baseline, then complete increments.
Deployment/DNS work must use separately granted session authority and verified
values. Live model experiments remain disabled throughout this implementation.

## Consequential choices

- Migration scope is 2–6 accounts, one complete snapshot, integer USD cents,
  bijective identity correspondence, fresh SQLite destination. Signed balances
  are allowed; splits, mergers and mixed currencies are unsupported.
- Bounded ambiguity search enumerates at most 720 mappings. Larger inputs are
  visibly rejected; no general solver or unrestricted permutation enumeration.
- Synthetic authority is a distinct evidence port. The evaluator receives only
  accepted observations; test grading retains its own expected correspondence.
- Independent checking shares the declared specification but does not call the
  witness constructor or use a model verdict. Hashes bind content, not truth.

## Increment 1 evidence

Baseline: 65 existing tests passed (8.48 seconds). The new migration suite has
103 passing cases: 100 generated seeds over 2–6 accounts plus fault-mode,
atomicity/admission, and corruption tests. These are bounded core checks, not a
completed acceptance audit. In particular M07 still needs equal-balance and
independently constructed grading families; M08–M10 remain unfinished.

Reproduce the core and its three receipt bundles:

```powershell
uv run pytest tests/test_migration.py -q
uv run python scripts/migration_validation.py
```

`migration.py` contains strict contracts, finite evidence evaluation, action
selection and direct witness verification. `migration_execution.py` performs
parameterized transactions and independently reads committed rows.
`migration_demo.py` supplies a synthetic authority through the evidence port
and orchestrates preview, evidence, repair, simulated admission and replay.
The service API is usable independently of Streamlit. Formal status remains
`not_verified_for_this_build` until the mandatory migration proofs run.

Observed/repair record:

- An initial collection failure exposed eager self-referential type annotations;
  deferred annotations fixed it. Import and strict typing checks prevent recurrence.
- Windows cleanup exposed SQLite connections surviving transaction context exit.
  Explicit connection closing now permits temporary directory cleanup after runs.
- Partial evidence fixed all but one mapping; the execution observer initially
  failed to infer the last pair under the declared bijection. The separate observer
  now reconstructs that pair. Generated four-to-six-account cases cover this path.

Review perspectives: the first core increment demonstrates a completed repair,
not just a block; the engineer can reproduce actual rows and offline evaluation;
the skeptic can inspect the finite scope, evidence port, exact admission binding,
and explicit absence of a formal/Python execution equivalence claim. Visitor
comprehension and default-page review require the upcoming UI increment.
