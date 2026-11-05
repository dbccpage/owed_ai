# `anomalon_workbench.storage`

Source: `src/anomalon_workbench/storage.py`

Transactional single-run admission, append-only decisions, content-addressed artifacts.

## class `Store`

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

### `artifact`

```python
def artifact(self, value: JsonValue) -> str
```

_No docstring yet._

### `read`

```python
def read(self, key: str) -> dict[str, JsonValue]
```

_No docstring yet._

### `enqueue`

```python
def enqueue(self, request_id: str, spec: dict[str, JsonValue], config: dict[str, JsonValue]) -> str
```

_No docstring yet._

### `claim`

```python
def claim(self, run_id: str, pid: int) -> bool
```

_No docstring yet._

### `get`

```python
def get(self, run_id: str) -> dict[str, JsonValue]
```

_No docstring yet._

### `list_runs`

```python
def list_runs(self) -> list[dict[str, JsonValue]]
```

_No docstring yet._

### `event`

```python
def event(self, run_id: str, event: dict[str, JsonValue]) -> None
```

_No docstring yet._

### `events`

```python
def events(self, run_id: str) -> list[dict[str, JsonValue]]
```

_No docstring yet._

### `cancel`

```python
def cancel(self, run_id: str) -> None
```

_No docstring yet._

### `cancelled`

```python
def cancelled(self, run_id: str) -> bool
```

_No docstring yet._

### `finish`

```python
def finish(self, run_id: str, status: str, receipt: dict[str, JsonValue]) -> None
```

_No docstring yet._

### `recover`

```python
def recover(self) -> int
```

Never resubmit uncertain requests. Mark workers interrupted after their maximum deadline.

### `admit`

```python
def admit(self, run_id: str, actor: str) -> str
```

_No docstring yet._

### `active_prompt`

```python
def active_prompt(self) -> dict[str, JsonValue] | None
```

_No docstring yet._
