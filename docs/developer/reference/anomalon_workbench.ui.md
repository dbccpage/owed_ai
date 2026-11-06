# `anomalon_workbench.ui`

Source: `src/anomalon_workbench/ui.py`

Python-authored UI: narrative first, raw evidence one click away.

## Functions

### `current_principal`

```python
def current_principal() -> Principal
```

_No docstring yet._

### `check_store_access`

```python
def check_store_access(store: Store) -> None
```

_No docstring yet._

### `start_button`

```python
def start_button(lab: Literal['ledger', 'graph', 'revision'], payload: dict[str, JsonValue], store: Store | None, provider: str, model: str) -> None
```

_No docstring yet._

### `ledger_page`

```python
def ledger_page(store: Store | None, provider: str, model: str) -> None
```

_No docstring yet._

### `graph_page`

```python
def graph_page(store: Store | None, provider: str, model: str) -> None
```

_No docstring yet._

### `revision_page`

```python
def revision_page(store: Store | None, provider: str, model: str) -> None
```

_No docstring yet._

### `show_review`

```python
def show_review(receipt: dict[str, JsonValue]) -> None
```

_No docstring yet._

### `inspector`

```python
def inspector(store: Store) -> None
```

_No docstring yet._

### `one_screen`

```python
def one_screen() -> None
```

The one-screen front page: what Owed knows, what it doesn't, and what finding out costs.

### `overview`

```python
def overview() -> None
```

_No docstring yet._

### `main`

```python
def main() -> None
```

_No docstring yet._
