# `anomalon_workbench.migration_execution`

Source: `src/anomalon_workbench/migration_execution.py`

Parameterized SQLite execution with content-bound simulated admission.

## class `Admission` (Record)

_No docstring yet._

Fields:

- `scenario: str`
- `candidate: str`
- `evidence: str`
- `policy: Literal['synthetic-migration/1']`
- `actor: Literal['simulated_operator']`

## class `Execution` (Record)

_No docstring yet._

Fields:

- `rows: tuple[tuple[str, int], ...]`
- `committed: bool`
- `total_preserved: bool`
- `row_count_preserved: bool`
- `identity_coverage: bool`
- `execution_conforms: bool`
- `ownership_preserved: bool | None`

## Functions

### `admit`

```python
def admit(scenario: Scenario, plan: Plan, observations: tuple[Observation, ...]) -> Admission
```

_No docstring yet._

### `execute`

```python
def execute(path: Path, scenario: Scenario, plan: Plan, observations: tuple[Observation, ...]=(), admission: Admission | None=None, *, preview: bool=False, interrupt_after: int | None=None) -> Execution
```

_No docstring yet._
