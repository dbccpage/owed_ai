# `anomalon_workbench.ledger`

Source: `src/anomalon_workbench/ledger.py`

Finite model evaluation. No model response is accepted as an observation.

## Functions

### `matches`

```python
def matches(a: int, b: int, obs: Observation) -> bool
```

_No docstring yet._

### `evaluate`

```python
def evaluate(data: LedgerInput) -> LedgerEvaluation
```

_No docstring yet._

### `verify`

```python
def verify(data: LedgerInput, result: LedgerEvaluation) -> bool
```

Separate direct predicate/count implementation, including every returned witness.
