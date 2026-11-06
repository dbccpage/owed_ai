# `anomalon_workbench.cognition`

Source: `src/anomalon_workbench/cognition.py`

A bounded cognitive review: make contradictions and next checks easy to inspect.

This audits structured evidence boundaries, not psychology or truth of arbitrary prose.
It is a companion assessment and never rewrites the original receipt or grants authority.

## class `ReviewSignal` (Record)

_No docstring yet._

Fields:

- `code: str`
- `detail: str`

## class `CognitiveReview` (Record)

_No docstring yet._

Fields:

- `version: str`
- `source_hash: str`
- `question: str`
- `checked_result: str`
- `signals: tuple[ReviewSignal, ...]`
- `next_check: str`
- `scope: str`

## Functions

### `review`

```python
def review(spec: RunSpec, result: dict[str, JsonValue]) -> CognitiveReview
```

_No docstring yet._

### `review_receipt`

```python
def review_receipt(receipt: dict[str, JsonValue]) -> dict[str, JsonValue]
```

Bind an independent review to an unchanged semantic receipt.
