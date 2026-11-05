# `anomalon_workbench.spending`

Source: `src/anomalon_workbench/spending.py`

Process-safe reservations shared across tenants; uncertain calls keep their charge.

## class `SpendLedger`

_No docstring yet._

### `__init__`

```python
def __init__(self, root: Path)
```

_No docstring yet._

### `connection`

```python
def connection(self) -> sqlite3.Connection
```

_No docstring yet._

### `admit_run`

```python
def admit_run(self, run: str, owner: str, policy: HostedPolicy, seconds: int) -> bool
```

_No docstring yet._

### `release_run`

```python
def release_run(self, run: str) -> None
```

_No docstring yet._

### `reserve`

```python
def reserve(self, run: str, owner: str, policy: HostedPolicy) -> str
```

_No docstring yet._

### `settle`

```python
def settle(self, key: str, cost: float | None) -> None
```

_No docstring yet._

### `usage`

```python
def usage(self, owner: str) -> dict[str, JsonValue]
```

_No docstring yet._

## class `MeteredProvider`

_No docstring yet._

### `__init__`

```python
def __init__(self, provider: ModelProvider, ledger: SpendLedger, run: str, principal: Principal)
```

_No docstring yet._

### `generate`

```python
def generate(self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float) -> ModelReply
```

_No docstring yet._
