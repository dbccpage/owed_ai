# `anomalon_workbench.service`

Source: `src/anomalon_workbench/service.py`

One bounded application service shared by worker, CLI, UI and replay.

## class `Runtime`

_No docstring yet._

### `__init__`

```python
def __init__(self, provider: ModelProvider, spec: RunSpec, emit: Callable[[dict[str, JsonValue]], None]=lambda event: None, cancelled: Callable[[], bool]=lambda: False)
```

_No docstring yet._

### `check`

```python
def check(self) -> None
```

_No docstring yet._

### `ask`

```python
def ask(self, system: str, user: str, kind: type[R]) -> R
```

_No docstring yet._

## class `ReplayProvider`

_No docstring yet._

### `__init__`

```python
def __init__(self, calls: list[dict[str, JsonValue]])
```

_No docstring yet._

### `generate`

```python
def generate(self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float) -> ModelReply
```

_No docstring yet._

## Functions

### `unique_object`

```python
def unique_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]
```

_No docstring yet._

### `parse_record`

```python
def parse_record(text: str, record: type[R]) -> R
```

_No docstring yet._

### `evaluate_ledger`

```python
def evaluate_ledger(runtime: Runtime) -> dict[str, JsonValue]
```

_No docstring yet._

### `evaluate_graph`

```python
def evaluate_graph(runtime: Runtime) -> dict[str, JsonValue]
```

_No docstring yet._

### `evaluate_revision`

```python
def evaluate_revision(runtime: Runtime) -> dict[str, JsonValue]
```

_No docstring yet._

### `execute`

```python
def execute(runtime: Runtime, config: dict[str, JsonValue]) -> dict[str, JsonValue]
```

_No docstring yet._

### `replay`

```python
def replay(receipt: dict[str, JsonValue]) -> bool
```

_No docstring yet._
