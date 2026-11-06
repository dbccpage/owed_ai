# `anomalon_workbench.tuner`

Source: `src/anomalon_workbench/tuner.py`

A small learning loop with five verbs: propose, evaluate, authorize, record, learn.

The loop watches a system's own receipts, proposes typed candidate changes,
tests each candidate against recorded history, and lets a separate authorizer
decide. Nothing self-applies: a candidate reaches the caller's ``apply``
callback only after a ``supported`` verdict and an ``approved`` authorization,
and every step is appended to a hash-chained receipt log that can be replayed.

Design rules enforced here, not merely documented:

- Proposer, evaluator and authorizer are three distinct objects. ``Loop``
  refuses to start when one object fills two roles, and refuses an
  authorization whose ``authorizer`` name equals the candidate's ``origin``.
- Verdicts are ``supported``, ``refuted`` or ``underdetermined``; only
  ``supported`` may be authorized. ``underdetermined`` always needs a human.
- ``learn`` builds a mistake memory from refuted receipts. Every proposal is
  checked against it first, so a refuted candidate is not proposed twice.
- Receipts are content-addressed (SHA-256 over canonical JSON including the
  previous hash). ``ReceiptLog.verify`` finds the first broken link.

Standard library only. ``numpy`` is never required. This file is the reference
implementation; a verbatim copy may be vendored by another project, which
records the source revision it copied.

## class `TunerError` (Exception)

Base class for refusals raised by the loop.

## class `RoleConflict` (TunerError)

One object was offered for two of proposer / evaluator / authorizer.

## class `SelfAuthorization` (TunerError)

An authorization named the candidate's own origin as its authorizer.

## class `ReceiptChainBroken` (TunerError)

A receipt's hash does not match its content or its predecessor.

## class `Candidate`

A typed proposed change. ``payload`` must be JSON-serialisable.

Fields:

- `kind: str`
- `payload: Mapping[str, Any]`
- `origin: str`
- `rationale: str`

### `candidate_id`

```python
def candidate_id(self) -> str
```

_No docstring yet._

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

## class `Verdict`

What recorded history says about a candidate, with the numbers behind it.

Fields:

- `status: VerdictStatus`
- `evaluator: str`
- `reason: str`
- `evidence: Mapping[str, Any]`

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

## class `Authorization`

_No docstring yet._

Fields:

- `status: AuthorizationStatus`
- `authorizer: str`
- `reason: str`
- `policy_id: str`

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

## class `Policy`

A declared authorization rule. Anything not covered needs a human.

Fields:

- `policy_id: str`
- `auto_approve_kinds: frozenset[str]`
- `human_review_kinds: frozenset[str]`
- `min_improvement: float`
- `improvement_key: str`
- `max_applied_per_run: int | None`

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

## class `Receipt`

_No docstring yet._

Fields:

- `seq: int`
- `step: ReceiptStep`
- `candidate_id: str`
- `body: Mapping[str, Any]`
- `prev_hash: str`
- `hash: str`

### `compute_hash`

```python
def compute_hash(seq: int, step: str, candidate_id: str, body: Mapping[str, Any], prev_hash: str) -> str
```

_No docstring yet._

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

### `from_json`

```python
def from_json(cls, data: Mapping[str, Any]) -> Receipt
```

_No docstring yet._

## class `ReceiptLog`

Append-only, hash-chained receipts. ``verify`` returns the first bad index or -1.

### `__init__`

```python
def __init__(self, receipts: Iterable[Receipt]=()) -> None
```

_No docstring yet._

### `receipts`

```python
def receipts(self) -> tuple[Receipt, ...]
```

_No docstring yet._

### `head`

```python
def head(self) -> str
```

_No docstring yet._

### `append`

```python
def append(self, step: ReceiptStep, candidate_id: str, body: Mapping[str, Any]) -> Receipt
```

_No docstring yet._

### `verify`

```python
def verify(self) -> int
```

Return -1 when the whole chain is intact, else the index of the first bad receipt.

### `require_intact`

```python
def require_intact(self) -> None
```

_No docstring yet._

### `to_json`

```python
def to_json(self) -> list[Json]
```

_No docstring yet._

### `from_json`

```python
def from_json(cls, data: Iterable[Mapping[str, Any]]) -> ReceiptLog
```

_No docstring yet._

### `dumps`

```python
def dumps(self) -> str
```

_No docstring yet._

### `loads`

```python
def loads(cls, text: str) -> ReceiptLog
```

_No docstring yet._

## class `Mistake`

_No docstring yet._

Fields:

- `candidate_id: str`
- `kind: str`
- `reason: str`
- `evidence: Mapping[str, Any]`
- `receipt_seq: int`

## class `MistakeMemory`

Refuted candidates and why. Checked before any new proposal.

### `__init__`

```python
def __init__(self) -> None
```

_No docstring yet._

### `lookup`

```python
def lookup(self, candidate: Candidate) -> Mistake | None
```

_No docstring yet._

### `remember`

```python
def remember(self, mistake: Mistake) -> None
```

_No docstring yet._

### `mistakes`

```python
def mistakes(self) -> tuple[Mistake, ...]
```

_No docstring yet._

### `to_json`

```python
def to_json(self) -> list[Json]
```

_No docstring yet._

## class `Proposer` (Protocol)

_No docstring yet._

Fields:

- `name: str`

### `propose`

```python
def propose(self, context: Mapping[str, Any]) -> Sequence[Candidate]
```

_No docstring yet._

## class `Evaluator` (Protocol)

_No docstring yet._

Fields:

- `name: str`

### `evaluate`

```python
def evaluate(self, candidate: Candidate, history: Any) -> Verdict
```

_No docstring yet._

## class `Authorizer` (Protocol)

_No docstring yet._

Fields:

- `name: str`

### `authorize`

```python
def authorize(self, candidate: Candidate, verdict: Verdict, policy: Policy) -> Authorization
```

_No docstring yet._

## class `PolicyAuthorizer`

Authorizes from the declared ``Policy`` alone. Never consults the proposer.

### `__init__`

```python
def __init__(self, name: str='policy') -> None
```

_No docstring yet._

### `authorize`

```python
def authorize(self, candidate: Candidate, verdict: Verdict, policy: Policy) -> Authorization
```

_No docstring yet._

## class `RunSummary`

_No docstring yet._

Fields:

- `proposed: int`
- `skipped_known_mistakes: int`
- `supported: int`
- `refuted: int`
- `underdetermined: int`
- `approved: int`
- `denied: int`
- `needs_human: int`
- `deferred: int`
- `applied: int`
- `apply_failed: int`
- `applied_candidates: list[Candidate]`
- `pending_human: list[tuple[Candidate, Verdict, Authorization]]`

### `proposal_error_rate`

```python
def proposal_error_rate(self) -> float
```

Fraction of evaluated proposals that history refuted.

### `to_json`

```python
def to_json(self) -> Json
```

_No docstring yet._

## class `Loop`

Wire the five verbs together with the separation rules enforced.

### `__init__`

```python
def __init__(self, proposer: Proposer, evaluator: Evaluator, authorizer: Authorizer, policy: Policy, log: ReceiptLog | None=None, memory: MistakeMemory | None=None) -> None
```

_No docstring yet._

### `run_once`

```python
def run_once(self, context: Mapping[str, Any], history: Any, apply: Callable[[Candidate], Mapping[str, Any]] | None=None, run_label: str='') -> RunSummary
```

_No docstring yet._

## Functions

### `canonical_json`

```python
def canonical_json(value: Any) -> str
```

Deterministic JSON: sorted keys, no whitespace, ASCII only.

### `content_hash`

```python
def content_hash(value: Any) -> str
```

_No docstring yet._

### `propose`

```python
def propose(proposer: Proposer, context: Mapping[str, Any], memory: MistakeMemory | None=None) -> list[Candidate]
```

Ask ``proposer`` for candidates; stamp each with the proposer's name as origin.

Candidates already in ``memory`` are left in the result (the loop records them
as ``skipped_known_mistake``) so the caller can see what was filtered and why.

### `evaluate`

```python
def evaluate(evaluator: Evaluator, candidate: Candidate, history: Any) -> Verdict
```

_No docstring yet._

### `authorize`

```python
def authorize(authorizer: Authorizer, candidate: Candidate, verdict: Verdict, policy: Policy) -> Authorization
```

Run the authorizer, then enforce the separation rules on its answer.

### `record`

```python
def record(log: ReceiptLog, step: ReceiptStep, candidate: Candidate | str, body: Mapping[str, Any]) -> Receipt
```

_No docstring yet._

### `learn`

```python
def learn(receipts: Iterable[Receipt], memory: MistakeMemory | None=None) -> MistakeMemory
```

Fold refuted verdicts from ``receipts`` into a mistake memory.

### `replay`

```python
def replay(log: ReceiptLog) -> Json
```

Rebuild the loop's observable state from receipts alone (no live components).
