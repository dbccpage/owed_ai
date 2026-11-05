# `anomalon_workbench.migration_demo`

Source: `src/anomalon_workbench/migration_demo.py`

Synthetic authority adapter and reproducible application service; no provider calls.

## class `SyntheticAuthority`

Trusted only within this declared synthetic scenario. Never passed to evaluator.

### `__init__`

```python
def __init__(self, scenario: Scenario, mapping: Plan, mode: Mode='valid')
```

_No docstring yet._

### `obtain`

```python
def obtain(self, scope: Scope, action: EvidenceAction) -> Observation
```

_No docstring yet._

## class `Step` (Record)

_No docstring yet._

Fields:

- `selected_by: Literal['engine', 'visitor']`
- `action: EvidenceAction`
- `observation: Observation`
- `rationale: str`

## class `InvestigationEvent` (Record)

Informational probes never enter the accepted identity-observation list.

Fields:

- `kind: Literal['repeat_total', 'repeat_count']`
- `at_step: int`
- `result: int`
- `compatible_before: int`
- `compatible_after: int`
- `information_gained: Literal['none']`

## class `Receipt` (Record)

_No docstring yet._

Fields:

- `schema_version: Literal['migration/1', 'migration/2', 'migration/3']`
- `checker: Literal['migration/1', 'migration/2', 'migration/3']`
- `application_build: str`
- `run_id: str`
- `scenario: Scenario`
- `original: Plan`
- `preview: Execution`
- `initial: Evaluation`
- `initial_observations: tuple[Observation, ...]`
- `steps: tuple[Step, ...]`
- `observations: tuple[Observation, ...]`
- `final: Evaluation`
- `repaired: Plan | None`
- `admission: Admission | None`
- `execution: Execution | None`
- `formal_artifact: dict[str, JsonValue]`
- `investigations: tuple[InvestigationEvent, ...]`

### `binding`

```python
def binding(self) -> Receipt
```

_No docstring yet._

## Functions

### `fixture`

```python
def fixture(seed: int=0, count: int=3) -> tuple[Scenario, Plan, Plan]
```

Return public data + fixture candidate + authority-only correspondence.

Public rosters are shuffled independently. Crosswalk is supplied only to the
authority adapter, never to witness construction or evidence selection.

### `run`

```python
def run(scenario: Scenario, original: Plan, port: EvidencePort, initial_observations: tuple[Observation, ...]=(), *, prior: Receipt | None=None, acquire: bool=True, one_action: bool=False, requested_action: EvidenceAction | None=None) -> Receipt
```

_No docstring yet._

### `record_probe`

```python
def record_probe(receipt: Receipt, kind: Literal['repeat_total', 'repeat_count']) -> Receipt
```

Append a replay-checked observation of existing totals/counts; no SQL or authority.

### `investigation_timeline`

```python
def investigation_timeline(receipt: Receipt) -> list[dict[str, str | int]]
```

Interleave identity requests and probes in their recorded causal order.

### `export`

```python
def export(receipt: Receipt) -> str
```

_No docstring yet._

### `replay`

```python
def replay(raw: str) -> bool
```

Bounded offline re-evaluation; never queries authority or calls execute().

### `main`

```python
def main() -> None
```

_No docstring yet._
