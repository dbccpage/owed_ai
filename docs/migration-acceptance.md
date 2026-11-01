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

## Increment 2 evidence — November 1, 2026

The default public UI now implements staged preview → witness → selected evidence
→ repaired transaction → replay. Existing mathematical labs remain secondary.
273 tests pass locally (16.05 seconds), Ruff passes, and strict mypy passes for
21 modules. This supersedes the increment-1 counts without changing their history.

| ID | Current executable evidence | Status / remaining gate |
|---|---|---|
| M01 | `test_atomic_execution_and_exact_admission`; generated rows observed from separate SQLite connection | Local pass; container rerun pending |
| M02 | 100 generated witness checks; corrupted witness rejection | Pass within 2–6 account scope |
| M03 | `test_independent_case_families`; staged acquisition/reuse test | Pass locally; no optimal whole-strategy claim |
| M04 | Missing/stale/conflicting UI tests; unknown-endpoint evidence exclusion; timeout adapter test | Pass locally |
| M05 | Exact candidate and changed-snapshot denial tests | Pass for simulated operator only |
| M06 | Imported receipt size/digest checks, recomputed evaluations/actions/rows/flags, no-query/no-execute replay test | Local pass; deeper adversarial import audit still pending |
| M07 | 100 fixture seeds + 100 test-owned authority seeds; unequal/equal/negative balances, varied IDs/order, partial mappings, correct/incorrect candidates | Pass within declared bounds |
| M08 | `python scripts/check_migration_lean.py`; `evidence/migration-lean.json` | All 3 model theorems pass under Lean 4.19.0; conservation uses propext/Quot.sound, other two no axioms |
| M09 | `test_public_guided_migration_session_and_replay`; fault-mode UI tests | Session/isolation/journey pass in AppTest; actual desktop/mobile and comprehension review pending |
| M10 | `owed-migration`, 3 example receipts, `migration_validation.py`, walkthrough | Local artifacts present; release/container/hosted checks pending |

Timing is measured by `migration_validation.py` on Windows 11 / Python 3.12.12,
three accounts. See `evidence/migration-core.json` for raw seconds. These are core
timings, not time-to-first-browser-result or cold-start latency. The 15-second and
60–90-second comprehension targets remain unmeasured.

The first Lean attempt had a failed rewrite in the inverse-lookup proof; the checker
reported `sorryAx` and failed. It was replaced by congruence applied to the actual
left-inverse equation. The successful audit contains no placeholders/custom axioms.
`lean/Migration.lean` does not prove Python/SQL equivalence. Build evidence verifies
the exact Lean source hashes; each run separately checks committed database rows.

Before release, inspect the real responsive journey, verify package/container
inclusion, retain browser observations, refresh example receipts after source changes,
and run the full acceptance audit. The production service has not been changed by
these increments. Current release candidate is not declared complete.
