# `anomalon_workbench.migration_ui`

Source: `src/anomalon_workbench/migration_ui.py`

Guided synthetic migration presentation; all verification lives in services.

## Functions

### `dollars`

```python
def dollars(cents: int) -> str
```

Format integer cents without rounding or floating-point conversion.

### `comparison`

```python
def comparison(receipt: Receipt) -> list[dict[str, str]]
```

_No docstring yet._

### `source_commit`

```python
def source_commit() -> str | None
```

Render's runtime metadata, never a guess from a receipt fingerprint.

### `clear_evidence_result`

```python
def clear_evidence_result() -> None
```

_No docstring yet._

### `restart_walkthrough`

```python
def restart_walkthrough(consistent_records: bool=False) -> None
```

Shared callback for main-scene recovery and navigation restart.

### `customer_names`

```python
def customer_names(scenario: Scenario) -> dict[str, str]
```

_No docstring yet._

### `current_scenario`

```python
def current_scenario() -> tuple[Scenario, Plan, Plan]
```

_No docstring yet._

### `stored_receipt`

```python
def stored_receipt() -> Receipt | None
```

_No docstring yet._

### `investigation`

```python
def investigation(choice: str, source: str='', *, refresh: bool=False) -> None
```

Choose only public requests; hidden correspondence stays in the authority adapter.

### `primary_controls`

```python
def primary_controls(panel: DeltaGenerator, receipt: Receipt | None, phase: int) -> None
```

All primary transitions live here, independently of sidebar visibility.

### `controls`

```python
def controls(panel: DeltaGenerator, receipt: Receipt | None, phase: int) -> None
```

_No docstring yet._

### `replay_message`

```python
def replay_message(matched: bool) -> str
```

_No docstring yet._

### `consequence_panel`

```python
def consequence_panel(receipt: Receipt, phase: int, names: dict[str, str]) -> str
```

Keep the current ambiguity or correction beside the same account scene.

### `page`

```python
def page(panel: DeltaGenerator | None=None) -> None
```

_No docstring yet._

### `explanation_page`

```python
def explanation_page() -> None
```

_No docstring yet._

### `technical_page`

```python
def technical_page() -> None
```

_No docstring yet._

### `engineering`

```python
def engineering() -> None
```

_No docstring yet._
