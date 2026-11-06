# `anomalon_workbench.graphs`

Source: `src/anomalon_workbench/graphs.py`

Exact graph reconstruction and independently verifiable obstruction cycles.

## Functions

### `rational`

```python
def rational(text: str, digits: int=30) -> Fraction
```

_No docstring yet._

### `validate`

```python
def validate(graph: GraphInput) -> None
```

_No docstring yet._

### `evaluate`

```python
def evaluate(graph: GraphInput) -> GraphEvaluation
```

_No docstring yet._

### `verify`

```python
def verify(graph: GraphInput, certificate: Certificate) -> bool
```

Check only certificate equations; does not call the reconstruction algorithm.

### `repair`

```python
def repair(graph: GraphInput, changes: tuple[Repair, ...]) -> GraphInput
```

_No docstring yet._
