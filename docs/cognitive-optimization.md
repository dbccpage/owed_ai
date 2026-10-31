# Cognitive Optimization · first bounded slice

**Owed — The Accountable Agent Workbench** is the display title. Suggested repository slug: `owed-ai`; name availability and trademark clearance have not been checked. The Python package and `anomalon` CLI retain their names to preserve the existing interface.

The title creates one question that carries the whole demonstration: **What did the agent establish—and what does it still owe?** The home page answers it through three recognizable situations. Technical lineage appears after the concrete behavior, and editable JSON and full receipts sit behind disclosure controls.

## Source-grounded choices

The cognitive-operations sources discuss presentation order, overloaded attention, suppressed contradictory evidence, framing, and uncertainty. They also explicitly describe their mathematical cognitive models as bounded analogies requiring empirical tests. This release adopts inspectable software behaviors from those ideas:

| Design choice | Executable behavior | Evidence ceiling |
|---|---|---|
| One stable question | Question → checked result → next check on a result card | A presentation design, not a measured cognitive gain |
| Show contradictions | Compare model verdict against host verdict; flag unsupported certainty and proposed observation replacement | Structured-field mismatch detection, not arbitrary prose verification |
| Preserve counterexamples | Keep ledger witnesses and graph obstruction certificates visible | Exact evidence within the declared finite models |
| Resist framing and order effects | Test host outcomes under evidence permutation and a persuasive but irrelevant question prefix | Host-checker invariance; no claim that the LLM or humans are invariant |
| Avoid self-promotional drift | A tie or regression receives a `no_measured_improvement` finding | The measured synthetic cases only |
| Reduce review burden | Surface one unresolved evidence obligation before the raw trace | A hypothesis about comprehension, pending reader testing |

The cognitive review is a **companion artifact**, with its own version and a binding to the original receipt digest. It cannot alter evidence, approve a candidate, or rewrite a recorded result. `anomalon review RUN_ID` and the inspector expose the same assessment. A lack of findings is not a certificate of truth or safety.

## What to measure next

For a later user study, compare the compact result card with the raw receipt view using the same cases. Ask readers to identify (1) the actual checked claim, (2) the missing observation, and (3) whether action is authorized. Measure correctness, time to answer, and unsupported-action choices; counterbalance presentation order. Do not report improved comprehension until that comparison is actually run.

Inspected local sources:

- `omega_engine_cognitive_operations/documentation/cognitive_warfare.md`: attention, framing, order effects, and explicit empirical limitations.
- `omega_engine_cognitive_operations/documentation/cognitive_obstruction_modeling.md`: lost contradictions, information overload, and defensive checks; its manifold/cohomology descriptions are not implemented as a human-cognition model here.

This release uses no visitor profiling, hidden persuasion score, or claim to diagnose a reader's psychological state. Optimization is directed at comprehension and inspectable reasoning.
