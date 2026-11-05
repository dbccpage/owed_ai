# `anomalon_workbench.migration_proof`

Source: `src/anomalon_workbench/migration_proof.py`

Validate complete source-bound build evidence; never compile Lean in a public run.

## class `MigrationProofReport` (Record)

_No docstring yet._

Fields:

- `status: Literal['verified_during_build']`
- `version: str`
- `command: tuple[Literal['lean'], Literal['Migration.lean']]`
- `exit_status: int`
- `theorems: dict[str, tuple[str, ...]]`
- `source_sha256: dict[str, Annotated[str, Field(pattern='^[0-9a-f]{64}$')]]`
- `assumptions: str`
- `boundary: str`
- `output: str`

### `complete`

```python
def complete(self) -> MigrationProofReport
```

_No docstring yet._

## Functions

### `audit_migration_output`

```python
def audit_migration_output(output: str) -> dict[str, tuple[str, ...]]
```

Require each statement and exactly one permitted axiom audit per theorem.

### `proof_status`

```python
def proof_status() -> dict[str, JsonValue]
```

_No docstring yet._
