# Validation evidence · v0.0.1.0

The deployed migration challenge is documented in the
[requirements-to-tests report](../docs/migration-acceptance.md),
[browser observations](migration-browser.json), [core timings](migration-core.json),
and [three-theorem Lean audit](migration-lean.json). Historical ledger/provider
results below remain separate. The [PR review](migration-pr-review.json) binds the
reviewed head and merged tree; [deployment evidence](migration-deployment.json)
records the public Chrome journey at [owed.anomalon.com](https://owed.anomalon.com/),
the downloaded synthetic receipt, all four evidence modes and deferred live-launch gates. Live experiments
remain disabled.

Latest hosted-mode preparation is recorded in [hosted validation](hosted-validation.md),
including Linux container CI, OIDC protocol testing, isolation and spending controls.
The table below preserves the original local MVP validation baseline.

Validated locally on Windows with Python 3.12.12 on October 31, 2026.

| Layer | Observed result |
|---|---|
| Automated suite | 49 passed after the OpenRouter and browser fixes, including property-based arithmetic tests, adversarial certificates, provider contracts, strict-schema projection, Streamlit page tests, persistent replay feedback across rerenders without resubmission, a separate worker calling a local HTTP test server, cognitive-review invariance checks, and failed-attempt preservation. |
| Static checks | Ruff passes; strict mypy passes for 13 application modules. |
| Lean | All four named results checked with Lean 4.19.0. Three use no axioms; the sufficiency lemma uses only `propext`. No `sorryAx`, Mathlib, or native evaluation. |
| Frozen comparison | Checklist 10/10; executable obligations 10/10; deliberately weak proof-promotion baseline 4/10, including 4 unsupported acceptances out of 7 nonsupported inputs. |
| Live Anthropic | All three final lab runs completed using `claude-haiku-4-5-20251001` in native JSON-schema mode. Requests: 1 ledger, 1 graph, 9 revision. |
| Live OpenRouter | All three labs completed with `openai/gpt-4.1-mini` in native JSON-schema mode through SQLite → separate worker → persisted receipts → offline replay. Requests: 1 ledger, 1 graph, 9 revision; three matching replays. |
| Live graph repair | Original graph refuted; proposed repair independently checked as supported. No minimum-cost claim. |
| Live prompt revision | Both providers: parent 3/4, child 3/4, a tie. Neither candidate is **eligible** or **admitted**. OpenRouter improves on the conflicting-evidence case and regresses on the positive-evidence case. |
| Replay | All six current live bundles (three per provider) reproduce their semantic receipts with no model calls. |
| Cognitive review | Source-bound companion assessments flag mismatches and the measured tie without altering receipts. Host outcomes are invariant across tested evidence permutations and irrelevant authority framing. No human-comprehension improvement is claimed. |

Configurable OpenAI-compatible endpoints and keyless local endpoints have contract-test coverage. A local HTTP fixture was exercised through an actual worker process. These paths have not been represented as live-model-validated adapters in this release. No hosted CI or deployment was run.

The initial OpenRouter authentication failure is retained in `examples/failed/openrouter-expired-key/ledger.json` and replays as the same failure without network access. `openrouter-auth-check.json` records the historical expiry response; `openrouter-auth-current.json` records successful authentication after the operator replaced the key. No credential bytes are included.

The refreshed-key attempt `20261031T193343Z-f3db3650` then failed on its first request: OpenAI's strict schema rejected optional `evidence_requests`. One additional diagnostic request confirmed the cause (`openrouter-schema-failure.json`). The adapter now projects an independent transport schema requiring all object fields and removing defaults; empty collections are explicit, and the original strict host validator is unchanged. No model or provider fallback was used. The failed attempt remains under `examples/attempts/openrouter/`.

The successful attempt `20261031T193654Z-c432c060` is summarized in `openrouter-live.json`. Its eleven successful requests report 6,997 input tokens, 2,227 output tokens, and **$0.006362** total provider-reported cost, excluding earlier rejected requests with unknown cost. The three worker runs took 2.719, 2.281, and 19.359 seconds. Each persisted its companion cognitive review. These observations are not a cost cap or a fresh-generation reproducibility claim.

The OpenRouter ledger retained 121 compatible states (101 satisfying, 20 falsifying) and denied viewer release. The graph preserved the original obstruction and verified the proposed `C−A=2` repair. The model labeled the original graph `inconsistent`; the checker used `refuted` for the claim that a global potential exists, and the mismatch remains visible. The revision parent passed both development cases, so its recorded failure-reference list is empty. The child later misclassified the positive case while fixing the parent's held-out conflict error: aggregate equality conceals that case-level regression.

Validation-runner repairs: live validation now uses the application's separate worker and persisted receipts, saves each attempt to a unique directory, records usage/timing/progress, and exits nonzero for failure or incomplete scope. Only successful replay-matching runs enter the current live examples. The UI's recorded-demo picker now includes every provider rather than only Anthropic.

Browser inspection exposed two presentation issues: available cost was omitted, and the two-second inspector refresh erased replay feedback. The inspector now displays provider-reported cost when complete and retains the replay result in session state bound to the receipt hash. The updated-key server was restarted; the completed OpenRouter revision was inspected in the browser. CLI export followed by offline replay also matched.

`anthropic-live.json` records final run statuses and receipt digests. `fixture-comparison.json` reports raw numerators, denominators, and individual cases. `lean-verification.json` records exact theorem output, axiom dependencies, toolchain, and source hashes. `source-manifest.json` identifies the inspected research documents. `release-manifest.json` binds the delivered source and examples after validation.

## Retained failures

The first JSON-prompt attempts returned Markdown-fenced JSON and were rejected. The first native-schema revision attempt failed at request eight because a purported ledger repair exceeded the supported repair schema. These artifacts remain in `examples/failed/`, including the successful ledger and graph runs from that intermediate attempt. They are historical evidence, not the final release demonstration.

The ledger instruction was then clarified: missing/corrected observations must be requested, not repaired. The final run completed, but the child still did not improve its score. Model prose remains provisional even when the verdict is correct; the score evaluates categorical verdicts only.

Historical bundles bind the prompts used at the time. Their hashes remain verifiable, but strict replay against the final prompts may reject them. Do not rewrite their transcripts to make them look current. Successful current bundles live in `examples/live/anthropic/` and `examples/live/openrouter/`.

The initial restricted test attempt encountered Windows temporary-directory ACL failures; Streamlit's asyncio socket-pair setup also hung inside the sandbox. The complete suite passed with a writable test directory and permission for local sockets. No tests were weakened or skipped for those environment failures.

The fixture suite establishes behavior on its declared cases. The checklist tie does not support a claim that executable obligations reason better than a carefully authored checklist. Their demonstrated benefit is explicit witnesses, inspection, and enforcement. No runtime-performance benchmark or general-model-improvement claim is made.
