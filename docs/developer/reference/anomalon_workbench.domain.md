# `anomalon_workbench.domain`

Source: `src/anomalon_workbench/domain.py`

Immutable contracts and canonical, finite semantic data.

## class `Record` (BaseModel)

_No docstring yet._

## class `Verdict` (StrEnum)

_No docstring yet._

## class `Claim` (Record)

_No docstring yet._

Fields:

- `id: str`
- `predicate: Literal['a >= 0 and b >= 0']`
- `question: str`
- `model_version: Literal['ledger/1']`
- `units: str`
- `snapshot: str`
- `intended_use: str`

## class `Observation` (Record)

_No docstring yet._

Fields:

- `field: Literal['total', 'b', 'b_nonnegative']`
- `value: int | bool`
- `source: str`
- `snapshot: str`
- `units: str`
- `adapter: Literal['ledger/1']`

## class `LedgerInput` (Record)

_No docstring yet._

Fields:

- `claim: Claim`
- `observations: tuple[Observation, ...]`
- `actor: Literal['viewer', 'operator']`

## class `Obligation` (Record)

_No docstring yet._

Fields:

- `claim_id: str`
- `reason: str`
- `evidence_needed: str`
- `checker: str`
- `role: str`
- `scope: str`
- `state: Literal['open', 'discharged', 'failed', 'waived']`

## class `Authorization` (Record)

_No docstring yet._

Fields:

- `actor: str`
- `action: str`
- `allowed: bool`
- `reason: str`
- `policy_version: str`

## class `LedgerEvaluation` (Record)

_No docstring yet._

Fields:

- `verdict: Verdict`
- `compatible: int`
- `satisfying: int`
- `falsifying: int`
- `witnesses: tuple[tuple[int, int], ...]`
- `accepted: tuple[Observation, ...]`
- `obligations: tuple[Obligation, ...]`
- `authorization: Authorization`
- `proof_status: Literal['not_checked']`
- `total_checked: bool`
- `assumptions: tuple[str, ...]`

## class `Edge` (Record)

_No docstring yet._

Fields:

- `id: str`
- `source: str`
- `target: str`
- `difference: str`
- `editable: bool`

## class `GraphInput` (Record)

_No docstring yet._

Fields:

- `vertices: tuple[str, ...]`
- `edges: tuple[Edge, ...]`

## class `PotentialCertificate` (Record)

_No docstring yet._

Fields:

- `kind: Literal['potentials']`
- `values: dict[str, str]`

## class `CycleStep` (Record)

_No docstring yet._

Fields:

- `edge_id: str`
- `direction: Literal[-1, 1]`

## class `CycleCertificate` (Record)

_No docstring yet._

Fields:

- `kind: Literal['cycle']`
- `steps: tuple[CycleStep, ...]`
- `residual: str`

## class `GraphEvaluation` (Record)

_No docstring yet._

Fields:

- `verdict: Verdict`
- `certificate: Certificate | None`
- `reason: str`

## class `Repair` (Record)

_No docstring yet._

Fields:

- `edge_id: str`
- `difference: str`

## class `Proposal` (Record)

_No docstring yet._

Fields:

- `interpretation: str`
- `verdict: Literal['supported', 'refuted', 'underdetermined', 'inconsistent', 'not_evaluated']`
- `evidence_requests: tuple[str, ...]`
- `repairs: tuple[Repair, ...]`

## class `PromptRevision` (Record)

_No docstring yet._

Fields:

- `instructions: str`
- `rationale: str`

## class `PromptVersion` (Record)

_No docstring yet._

Fields:

- `core: Literal[CORE]`
- `instructions: str`
- `parent_hash: str | None`
- `mutation: str`
- `failure_refs: tuple[str, ...]`

## class `Limits` (Record)

_No docstring yet._

Fields:

- `requests: int`
- `seconds: int`
- `output_tokens: int`

## class `RunSpec` (Record)

_No docstring yet._

Fields:

- `lab: Literal['ledger', 'graph', 'revision']`
- `payload: dict[str, JsonValue]`
- `limits: Limits`

## class `ModelReply` (Record)

_No docstring yet._

Fields:

- `content: str`
- `input_tokens: int | None`
- `output_tokens: int | None`
- `cost: float | None`

## class `ProviderFailure` (Exception)

Public, secret-free error code; never carries provider response bodies.

## class `ModelProvider` (Protocol)

_No docstring yet._

### `generate`

```python
def generate(self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float) -> ModelReply
```

_No docstring yet._

## class `CertificateVerifier` (Protocol)

_No docstring yet._

### `verify`

```python
def verify(self, graph: GraphInput, certificate: Certificate) -> bool
```

_No docstring yet._

## class `Experiment` (Protocol)

_No docstring yet._

### `evaluate`

```python
def evaluate(self, payload: dict[str, JsonValue]) -> dict[str, JsonValue]
```

_No docstring yet._

## class `RunStore` (Protocol)

_No docstring yet._

### `artifact`

```python
def artifact(self, value: JsonValue) -> str
```

_No docstring yet._

### `cancelled`

```python
def cancelled(self, run_id: str) -> bool
```

_No docstring yet._

## Functions

### `canonical`

```python
def canonical(value: object) -> str
```

_No docstring yet._

### `digest`

```python
def digest(value: object) -> str
```

_No docstring yet._

### `json_object`

```python
def json_object(model: BaseModel) -> dict[str, JsonValue]
```

_No docstring yet._
