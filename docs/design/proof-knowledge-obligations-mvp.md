# Proof, evidence, and outstanding obligations MVP

Owner: Jeremy H. Carroll  
Created: October 31, 2026  
Version: 0.1 — experiment definition and proposed build plan  
Status: Specified; not implemented or experimentally validated in this document

## Purpose

Build a small, reproducible system that distinguishes a checked formal result from a claim supported by the available evidence, and from permission to act on that claim. It must identify the assumptions, information loss, unresolved obligations, and authority relevant to a specific question.

The initiating statement is Jeremy's reply on Threads: “The real revolution will be machines that can distinguish what they have proved from what they actually know and identify precisely what they still owe.”

Here, “known” has a deliberately bounded operational meaning: the target claim is supported throughout the explicitly represented states compatible with accepted evidence, under a declared model and scope. The system does not certify that its model exhausts reality or that its evidence sources are truthful. Those dependencies remain visible.

This is a test of an inference boundary, not an experiment establishing that ASI is impossible. Lean is a component of the proposed solution. Definitions, assumptions, evidence adapters, and acceptance policies require their own treatment; a successful proof check does not automatically discharge them.

## The first experiment

Use a synthetic two-reserve ledger. Reserve values are signed integers in one fixed unit and one snapshot. A negative value represents a deficit. No financial recommendation or real account data is involved.

The declared finite state space is:

`S = {(a, b) : a is an integer, 0 <= a <= 120, b = 100 - a}`

The observation exposes only the total:

`Q(a, b) = a + b`

The requested target claim is:

`P(a, b) = (a >= 0 and b >= 0)`

The checked total statement is:

`T(q) = (q >= 100)`

Two states establish the issue:

| State | Observed total Q | Total statement T | Target claim P |
| --- | --- | --- | --- |
| (80, 20) | 100 | True | True |
| (120, -20) | 100 | True | False |

A valid proof that the observed total meets the threshold does not establish that both reserves are nonnegative. Both states have the same observation. Their different answers to P provide a finite ambiguity witness.

Proposed Lean results:

1. Both witness states belong to S.
2. Their observations agree and their target truth values differ.
3. There is no function `d : Int -> Bool` that correctly decides P for every state in S using only Q.
4. Within S, observing whether b is nonnegative is sufficient to decide P, because the declared domain already constrains a to be nonnegative.

Result 3 concerns exact decision on this domain. It does not exclude a probabilistic guess, abstention, a restricted domain, or success with additional observations.

The comparison must use only artifacts derived from the declared observation and public model. A purported proof artifact that embeds a hidden state, additional premise, or oracle response introduces more information and must be recorded as such.

## How the system should answer

For each admissible input, construct the compatible set `C = {s in S : s agrees with the accepted observations}`. Return:

- **Supported within scope:** C is nonempty and every state in C satisfies P.
- **Refuted within scope:** C is nonempty and every state in C falsifies P.
- **Underdetermined:** C contains both satisfying and falsifying states; return one of each as a witness.
- **Inconsistent evidence or model:** C is empty. Never report success by vacuous truth.
- **Not evaluated:** the checker failed, the input is unsupported, or required processing has not completed. An execution error is not a refutation.

Proof status and permission to act are separate fields. A proof can remain valid while the requested claim is underdetermined or an action is unauthorized.

With total-only evidence, all 121 states remain compatible: 101 satisfy P and 20 do not. Those counts are a mathematical prediction, not an observed experiment result or a probability distribution over reality.

## The obligation that resolves the ambiguity

Initially, the system should report: “The total is established within the model. Individual nonnegativity is underdetermined. Obtain an observation distinguishing the two classes, such as whether reserve B is nonnegative, from the same snapshot.”

For this finite domain, the single Boolean `b >= 0` suffices; without any additional discriminating information, the two witness states remain indistinguishable. This is a one-bit sufficiency and zero-additional-information impossibility result within the model, not a universal minimum-information theorem.

Then show two branches:

- Evidence `b = 20` resolves the claim as supported within scope.
- Evidence `b = -20` resolves the claim as refuted within scope.

The source, units, snapshot, adapter, and evidence integrity must match. If the evidence belongs to another snapshot, the fresh claim remains unresolved. A content hash binds bytes; it does not establish that the source observation is true.

An obligation record includes its triggering claim, reason, evidence needed, checker, responsible role, scope, and state: open, discharged, failed, or explicitly waived. Waiver is a policy event, never a proof or new observation. A failed condition may require changing the underlying state and submitting new evidence; it is not merely missing paperwork.

## Minimum system contract

| Record | Required content |
| --- | --- |
| Claim | ID, exact predicate, informal question, state-space version, units, snapshot, intended use |
| Formal result | Theorem statement, source/build hashes, Lean version, dependency lock, axiom dependencies, check outcome |
| Assumptions | Logical premises and model restrictions, separately from empirical premises; evidence or unresolved status for each |
| Observation | Source, snapshot, content hash, schema, adapter version, exposed fields, declared projection |
| Evaluation | Compatible-state counts, target verdict, ambiguity or counterexample witnesses, checker version |
| Obligations | Missing information, scope checks, contradictions, and required evidence or review |
| Authority | Actor/role, permitted action, policy version, scope, and separate authorization decision |
| Receipt | Bound input and output hashes, reproducibility metadata, statuses, and dependencies |

Do not collapse these into one green “verified” badge or confidence score. Keep logical validity, evidence support, and authorization inspectable separately.

The MVP uses an explicit fixture manifest to specify intended meaning. It checks schemas and the declared mapping; it does not autonomously infer or prove that the author's English specification captures the intended real-world problem. A human review of that mapping is recorded as an attestation with scope, not converted into mathematical truth.

## Proposed implementation

Use a Windows-native Python CLI for fixtures, finite enumeration, obligation tracking, and JSON receipts, plus a small pinned Lean 4 project for the finite results. Do not require an API key, LLM, cloud service, or paid compute for the first demonstration.

Keep the proposal input behind a plain JSON interface so a human, an LLM, or another program can supply it later. The evaluator must not trust the proposer's status labels.

Suggested components:

1. Typed claim and evidence records.
2. Lean proof-check adapter with axiom auditing.
3. A finite checker implemented separately from the proof adapter.
4. An obligation evaluator and deterministic report generator.
5. A policy gate governing only a simulated action.
6. Fixtures, mutation cases, and one replay command.

Separately implemented checkers can still share a mistaken specification. Agreement strengthens implementation evidence; it does not settle model adequacy.

Fail proof acceptance on `sorryAx` or undeclared axiom dependencies. Record and enforce a declared axiom policy; do not reject standard Lean axioms merely because they are axioms. Record any expanded trust caused by native evaluation, or exclude it from the first slice. Audit named theorem statements as well as compilation success.

Initially, authority is a local test configuration with explicit roles, not production identity management. Demonstrate that an unauthorized actor cannot release the simulated action, even when P is supported. If exceptions are implemented, preserve the unresolved verdict and record the override separately. No real deployment or external side effect is part of this experiment.

Existing PFP and LGGR code are candidates for reuse after inspection. No compatibility or completed integration is claimed here. Choose the smallest independently runnable slice rather than importing an entire research programme.

## Comparison design

| Condition | Behavior | Purpose |
| --- | --- | --- |
| A: Proof-status promotion | A deliberately weak integration promotes a checked total theorem to acceptance of P | Demonstrate the specific category error; not a characterization of Lean or all AI systems |
| B: Explicit checklist | An engineer-authored checklist asks about scope, missing evidence, and permission | Test whether a simpler process already provides the same protection |
| C: Executable obligations | The MVP computes compatible states and emits witnesses, obligations, and a separate authorization result | Test reproducibility, precision, and enforceable separation |

Use identical visible inputs for all conditions. The evaluator must not receive hidden fixture truth; the scoring harness may use it. Freeze expected outcomes before running comparisons. Include mutation cases after the basic cases pass. Publish cases, outputs, errors, and timing, not only a favorable example.

Repeating or adding consequences of the same observation does not distinguish states within its unchanged compatible set. If a new theorem uses a stronger assumption or new observation, record that change rather than attributing the gain to proof count alone.

## Required cases and acceptance criteria

| Case | Expected behavior |
| --- | --- |
| Total-only evidence | Underdetermined; valid ambiguity witness |
| Matching evidence b = 20 | Supported within scope |
| Matching evidence b = -20 | Refuted within scope |
| Evidence from another snapshot | No discharge of the current evidence obligation |
| Adapter treats dollars as cents | Scope/schema failure; no silent acceptance |
| Individually contradictory observations | Inconsistent evidence/model, not vacuous support |
| Proof proves total, user asks about every reserve | Retain the distinction between predicates |
| Proof uses a new premise equivalent to P | Expose that premise; do not count it as independent evidence for P |
| Changed bytes with old receipt | Integrity failure |
| Supported claim, wrong actor | Supported claim plus denied authorization |
| Checker timeout or crash | Not evaluated; no fabricated negative result |

Report unsupported acceptance, supported-case acceptance, correct refutation, correct abstention, obligation accuracy, integrity failures detected, and reproducibility. Report raw numerators and denominators. A system that abstains on every input fails the supported and refuted cases.

MVP completion requires every frozen fixture to match its expected multidimensional outcome, independent checking of all returned witnesses, successful proof and axiom checks, and reproducible semantic receipts on rerun. Keep wall-clock timestamps outside the deterministic payload. Runtime measurements must state hardware and scope; no benchmark claims before measurement.

A stronger comparative claim is not earned if C performs no better than B. Even then, inspectable receipts or automated enforcement may be useful, but report that narrower benefit. A small synthetic suite establishes behavior only on that suite.

## Build sequence and demonstration

Target approximately one working week, subject to repository inspection:

1. Freeze the finite model, vocabulary, fixtures, and expected outputs.
2. Implement enumeration, compatible-state verdicts, witnesses, and evidence obligations.
3. Add the Lean results, pinned toolchain, and axiom audit.
4. Add receipt binding, mutation checks, and simulated authorization.
5. Compare the three conditions, document failures, and record a three-minute walkthrough.

The walkthrough begins with a valid proof, asks the stronger question, shows the two indistinguishable states, requests the missing observation, resolves both branches, and finally shows that authorization remains a distinct decision.

Deliverables: runnable CLI; Lean sources; frozen fixtures; expected/actual results; sample receipts; short README; three-minute video. A dashboard, autonomous proposal generation, generalized theorem discovery, and production authentication are later work.

## Sources and limits

- [Jeremy's initiating reply](https://www.threads.com/@therealooutwire/post/DfC1fY-HM3k), text supplied in this conversation.
- [Jeremy's follow-up](https://www.threads.com/@therealooutwire/post/DfC1fX-HNd6), text supplied in this conversation.
- [Lean reference: Validating a Lean Proof](https://lean-lang.org/doc/reference/latest/ValidatingProofs/), consulted October 31, 2026; relevant to statement inspection, axiom auditing, and trust boundaries.
- [Lean reference: Axioms](https://lean-lang.org/doc/reference/latest/Axioms), consulted October 31, 2026. Pin the documentation/toolchain version during implementation.

The original finite example and experimental design above are proposed work. No experiment result, production adoption, universal epistemic completeness, or ASI conclusion is claimed.

## Revision log

| Date | Version | Change | Evidence or trigger |
| --- | --- | --- | --- |
| 2026-10-31 | 0.1 | Defined the finite experiment, obligations, comparisons, and implementation criteria | Jeremy's Threads replies and request to define an MVP |
