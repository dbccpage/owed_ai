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

## Increment 3 audit — November 1, 2026

The actual local browser journey now passes at 1280×900 and 390×844, including
committed repair, offline replay, downloaded export replayed by the CLI, scope
invalidation, missing/conflicting evidence, keyboard operation, another seed and
session reset. Mobile document width equals viewport width (390px). See
`evidence/migration-browser.json` and its screenshots. Human comprehension targets
remain unmeasured; these observations establish operability and readable layout.

Warm local automation measured 494ms from challenge click to a checked witness,
570ms for evidence-to-repaired result, and 2709ms for a fresh desktop tab to its
primary action. These single observations include automation overhead; they are
not a timing distribution or Render measurements.

The original PR head `d859cf3` passed [Linux/container CI](https://github.com/dbccpage/owed_ai/actions/runs/41344160907),
including an actual image build, health, uid 10001, public pages and volume restart.
The container smoke check now additionally exercises the full migration, proof
source match, replay and temporary cleanup; await its result at the current head.

Substantive review findings and recurrence conditions:

- **AB — missing evidence disclosure:** unavailable adapter responses initially
  carried correspondence links. They now carry none. The test asserts empty links
  and no secret exception text in the resulting receipt.
- **RL — import semantics:** recomputing a digest alone could permit false stored
  property flags or removal of a justified repair. Replay now verifies every
  execution flag, plan validity, identity coverage, version, action lineage and
  required repair presence. Adversarial tests recompute the outer hash and still
  require rejection.
- **SK — affected rows:** browser review showed a second changed witness row was
  not marked. The display now compares both mappings row by row, marking both.
- **HP — reload custody:** source reload changed Python class identity and falsely
  displayed an unchanged snapshot as stale. Session records are reconstructed
  through their canonical schema; serialized-session regression checks and the
  repeated browser journey preserve unchanged scope. Real scope changes still
  invalidate admission without rewriting history.
- **ASK — silent unavailable result:** a failed source request initially left only
  a generic mapping count. The UI now names source/status and explains why no
  repair is permitted; a fault-mode UI assertion prevents the silent presentation.

Local full suite at the beginning of this audit: 274 passed (12.53 seconds).
Final counts/current-head results are recorded after the last regression run.
M06's bounded import audit and M09's actual desktop/mobile operability review now
pass locally. Remaining release gate: final current-head validation and artifact
audit. Production migration publication and custom-domain/DNS setup are separate
operations; the current production release remains live-model-disabled.

Latest local regression run after the audit repairs: **274 passed in 23.61s**;
Ruff and strict mypy (21 modules) passed; all three mandatory migration proofs
passed. Three-account core repair was 15.76ms in that sample. These timings are
single local observations with different scopes; no broader performance claim.

## Final release-candidate audit

Audited application code: `466d53d0e210ba14af7b2dcdcd8e056a399bc27b`.
Its [extended Linux/container workflow](https://github.com/dbccpage/owed_ai/actions/runs/41345708824)
passed tests, Ruff, strict typing, actual Docker build and full migration execution
under uid 10001, proof-source matching, replay, temporary cleanup and volume restart.
The final documentation/configuration follow-up is tracked in draft PR #4.

| Acceptance IDs | Final result and evidence ceiling |
|---|---|
| M01–M02 | Pass: real transactions/rollback/rerun rejection, separate committed-row observer, independently verified ambiguity witnesses and corruption rejection |
| M03–M04 | Pass: explicit source port, finite informative-action selection, scope validation, missing/stale/invalid/conflicting evidence and tool failure behavior |
| M05–M06 | Pass: exact simulated admission binding, changed-input denial, safe bounded JSON replay, forged flags/lineage/repair rejection, no query or execution during replay |
| M07 | Pass: 200 seeds across two families, 2–6 accounts, varied IDs/order/amounts, equal/negative balances, partial/correct/incorrect mappings; no universal correctness or model-performance claim |
| M08 | Pass: all three Lean 4.19.0 statements and axiom audit, build source digest checks; Python/SQL conformance remains separate |
| M09 | Pass: default guided journey, browser keyboard interaction, 1280×900 and 390×844 layout, session reset/isolation, unavailable/conflicting branches, source-change invalidation and actual downloaded receipt replay |
| M10 | Pass: scriptable CLI, three reproducible receipts, named-environment timings, architecture/walkthrough/portfolio description, package and release/rollback instructions, reviewable draft PR |

Artifact audit: 125 manifest file digests matched both worktree and source-archive
members. Wheel/source builds succeeded and the configured-secret/private-data scan
passed. This is integrity evidence, not a signature or authentication of the author.

This completes the requested local implementation and release preparation. No PR
merge or migration production rollout is implied. The proposed hostname is
**owed.anomalon.com**; actual DNS/TLS setup, hosted migration validation, Google
live-operator verification and provider-side spending cap remain later release
operations. The existing public demo remains live-model-disabled. Human
comprehension targets are unmeasured; browser operability is verified, not human
learning outcomes or full accessibility certification.

### Subsequent domain connection — November 1, 2026

The owner completed Render/GoDaddy setup for `owed.anomalon.com`. Independent
public CNAME resolution and certificate-validated HTTPS health/app-shell probes
passed; see `evidence/domain-validation.json`. This supersedes the proposed-domain
status above. It does not alter the audited migration code, publish PR #4, or
complete Google/live-operator verification. No live-experiment configuration was
changed by this documentation operation.

### PR review and hosted rollout — November 1, 2026

PR #4 was independently reviewed at `c18d582f0ce3358cc4cfc542871bad13421edb92`:
274 tests passed in 19.45s, Ruff and strict mypy (21 modules) passed, and all three
migration Lean checks passed. Its Linux/container CI also passed. The merge commit
`86c2d90ee99fe4fb71330a524c390783260b596b` has the same source tree.
See `evidence/migration-pr-review.json` for the exact bindings.

The migration challenge is now deployed at https://owed.anomalon.com/ with live
model experiments disabled. Normal Chrome validation exercised the main journey,
receipt export and offline browser/CLI replay, valid/unsupported imports, the
source-bound proof artifact and snapshot invalidation. The current scoped report
in `evidence/migration-deployment.json` supersedes historical rollout-pending
statements above and explicitly lists any remaining hosted checks. Google login,
provider spending-cap configuration and human comprehension measurement remain
unverified.

Hosted completion: missing evidence remains unresolved; stale evidence is excluded
and a current-authority refresh enables the supported repair; contradictory evidence
has zero compatible mappings and admits no repair. Generation/reset passed for
seeds 0 and 1. Render confirms **Deploy succeeded / Live** for `86c2d90`, and the
live-experiment flag was rechecked as false after these tests. The public synthetic
release checks are complete; the deferred live-launch gates above remain separate.
