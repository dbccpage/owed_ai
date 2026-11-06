# Developer reference

Generated from the source by `scripts/build_reference.py`; do not edit by hand.
One page per module, listing each public class, its fields and methods, and the
module's public functions, with their docstrings.

| Module | Classes | Summary |
| --- | --- | --- |
| [`anomalon_workbench`](anomalon_workbench.md) | 0 | A bounded research workbench, not a general truth or authority oracle. |
| [`anomalon_workbench.cli`](anomalon_workbench.cli.md) | 0 | CLI entry point. All live work runs in a separate worker process. |
| [`anomalon_workbench.cognition`](anomalon_workbench.cognition.md) | 2 | A bounded cognitive review: make contradictions and next checks easy to inspect. |
| [`anomalon_workbench.comparison`](anomalon_workbench.comparison.md) | 0 | Independent, engineer-authored interval checklist; no call to the finite evaluator. |
| [`anomalon_workbench.domain`](anomalon_workbench.domain.md) | 26 | Immutable contracts and canonical, finite semantic data. |
| [`anomalon_workbench.examples`](anomalon_workbench.examples.md) | 0 | Public starter inputs; withheld labels are computed only in the evaluator. |
| [`anomalon_workbench.graphs`](anomalon_workbench.graphs.md) | 0 | Exact graph reconstruction and independently verifiable obstruction cycles. |
| [`anomalon_workbench.hosting`](anomalon_workbench.hosting.md) | 2 | Hosted admission boundary: verified OIDC claims, isolated stores, fixed provider. |
| [`anomalon_workbench.ledger`](anomalon_workbench.ledger.md) | 0 | Finite model evaluation. No model response is accepted as an observation. |
| [`anomalon_workbench.migration`](anomalon_workbench.migration.md) | 11 | Bounded migration contracts, evidence evaluation and independent certificates. |
| [`anomalon_workbench.migration_demo`](anomalon_workbench.migration_demo.md) | 4 | Synthetic authority adapter and reproducible application service; no provider calls. |
| [`anomalon_workbench.migration_execution`](anomalon_workbench.migration_execution.md) | 2 | Parameterized SQLite execution with content-bound simulated admission. |
| [`anomalon_workbench.migration_proof`](anomalon_workbench.migration_proof.md) | 1 | Validate complete source-bound build evidence; never compile Lean in a public run. |
| [`anomalon_workbench.migration_scene`](anomalon_workbench.migration_scene.md) | 0 | Escaped presentation only: no access to hidden ownership or selection logic. |
| [`anomalon_workbench.migration_ui`](anomalon_workbench.migration_ui.md) | 0 | Guided synthetic migration presentation; all verification lives in services. |
| [`anomalon_workbench.providers`](anomalon_workbench.providers.md) | 2 | Small explicit HTTP adapters. Credentials never enter public configuration. |
| [`anomalon_workbench.serve`](anomalon_workbench.serve.md) | 0 | Render entrypoint. Authentication secrets exist only in a private runtime file. |
| [`anomalon_workbench.service`](anomalon_workbench.service.md) | 2 | One bounded application service shared by worker, CLI, UI and replay. |
| [`anomalon_workbench.spending`](anomalon_workbench.spending.md) | 2 | Process-safe reservations shared across tenants; uncertain calls keep their charge. |
| [`anomalon_workbench.storage`](anomalon_workbench.storage.md) | 1 | Transactional single-run admission, append-only decisions, content-addressed artifacts. |
| [`anomalon_workbench.tuner`](anomalon_workbench.tuner.md) | 18 | A small learning loop with five verbs: propose, evaluate, authorize, record, learn. |
| [`anomalon_workbench.tuner_demo`](anomalon_workbench.tuner_demo.md) | 5 | Finite demo for the tuner loop: pin the right keys in a tiny cache. |
| [`anomalon_workbench.ui`](anomalon_workbench.ui.md) | 0 | Python-authored UI: narrative first, raw evidence one click away. |
| [`anomalon_workbench.worker`](anomalon_workbench.worker.md) | 0 | A separate bounded worker; reruns cannot claim an already-running job. |
