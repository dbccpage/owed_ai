# One engine, three bounded experiments

## Migration public journey

The default page now presents a separate bounded application service using the
same immutable-record and canonical-receipt conventions. `migration.py` evaluates
only passed observations, enumerating at most 720 bijections; its direct witness
checker reconstructs certificate conditions without invoking the constructor.
`migration_demo.py` obtains observations exclusively through `EvidencePort`.
`SyntheticAuthority` holds scenario correspondence outside that evaluator.
The seed reproduces fixtures; it is not an authority credential or evidence.

`migration_execution.py` renders typed plans through parameterized SQL into a fresh
database, rolls back interrupted transactions, closes connections, and reads committed
rows through a separate observer. Exact simulated admission binds scenario, plan,
policy and accepted evidence versions. Preview is explicitly unadmitted and isolated.
Temporary databases are removed after execution; only session receipts survive until
reset/restart. Public receipt imports are size bounded and never query or execute.

The migration supplement proves conservation for permutations of integer lists,
a concrete ownership counterexample, and conditional inverse-crosswalk preservation.
`migration_proof.py` checks the recorded Lean source hashes at runtime. This binds
model proof artifacts to shipped sources, not Python/SQL to Lean semantics.
Runtime row checks provide separate computational evidence. Neither proof status,
receipt replay nor an agent proposal grants production authority.

The UI and CLI construct the same `RunSpec`. SQLite admits one active run; a fresh Python worker atomically claims it. The worker calls application services, which use a provider port and exact domain checkers. It writes progress and a content-addressed receipt. The UI only reads that state and requests cancellation or human admission.

Hosted mode adds an outer admission boundary: Streamlit verifies an OIDC identity,
then `hosting.py` checks issuer, subject allowlist and expiry before opening that
operator's store. Anonymous visitors use the pure checkers and curated public
replays without opening any private store. Each private store retains its own
single-run constraint, artifacts and active prompt. `spending.py` coordinates a
shared concurrency lease and atomic per-request monetary reservation across stores.
Workers independently validate their scoped context before using the fixed hosted
provider. Billing reservations live outside deterministic semantic receipts.

```text
Streamlit / CLI → RunSpec → SQLite admission → Python worker
                                               ├─ model adapter → provisional JSON
                                               ├─ exact checker → independent certificate verification
                                               └─ receipt + events → inspector / offline replay
Human operator → explicit admission → immutable active prompt version
```

`domain.py` owns strict, frozen records and ports. `ledger.py` and `graphs.py` contain the finite mathematics. `comparison.py` implements a separately authored interval checklist. `service.py` owns bounded experiments and request-matching replay. `providers.py` contains explicit HTTP adapters; `storage.py` owns SQLite and artifact integrity; `worker.py` owns process execution. UI rendering is not imported by the domain.

The public proposal schema distinguishes an interpretation, a categorical verdict, evidence requests, and synthetic graph repairs. Proposed verdicts are never host verdicts. A schema can validate structure without validating the truth of prose. In particular, the four-case revision score grades verdict labels only.

Ledger assumptions are declared, not inferred: one snapshot, one unit, integer `a` in `[0,120]`, `b=100-a`. Wrong-unit data makes processing not evaluated; stale evidence is excluded and leaves an obligation. Contradictory accepted observations produce inconsistency. False target evidence produces refutation. Authorization requires a supported target, operator role, and no open or failed obligations.

Graph input is limited to eight vertices, sixteen edges, and bounded integer/fraction strings. The requested claim is existence of globally consistent potentials. A nonzero closed-walk residual refutes that existence claim. Graph repairs create new synthetic problems; they do not assert that external observations changed.

Prompt lineage separates immutable versions from execution occurrences. A child records its parent digest, mutation rationale, and failed development rows. Mutation gets no withheld cases or labels. Evaluation completes before admission, and no tool exposed to the model can insert an admission decision. Protected-core preservation is structural; it is not a theorem that all future model behavior obeys the core.

Semantic replay is deliberately strict about request hashes. A changed experiment prompt or schema can make an older bundle incompatible. Historical failed attempts remain integrity-checkable evidence even when the current engine refuses semantic replay. The shipped successful examples target this release's request contracts.

SQLite uses atomic admission and worker claim transitions. It does not automatically repeat provider requests following crashes or timeouts. A watchdog bounds the worker independently of HTTP timeout behavior. A watchdog-aborted run may contain only partial progress, and is not marked replay-complete.

No distributed queue, custom identity provider, vector store, generated-code executor,
or broad estate dependency is included. Hosted login integrates standard OIDC;
the loopback identity fixture is testing-only. Python `Protocol` ports permit later
adapters without importing those systems into this release.
