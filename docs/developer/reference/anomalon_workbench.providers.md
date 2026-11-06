# `anomalon_workbench.providers`

Source: `src/anomalon_workbench/providers.py`

Small explicit HTTP adapters. Credentials never enter public configuration.

## class `ProviderConfig`

_No docstring yet._

Fields:

- `provider: ProviderName`
- `model: str`
- `base_url: str`
- `output_mode: Literal['json_prompt', 'json_schema']`
- `key_env: str`
- `key: str`

### `from_env`

```python
def from_env(cls, provider: str | None=None, model: str | None=None) -> ProviderConfig
```

_No docstring yet._

### `validate`

```python
def validate(self) -> None
```

_No docstring yet._

### `public`

```python
def public(self) -> dict[str, JsonValue]
```

_No docstring yet._

### `restore`

```python
def restore(cls, data: dict[str, JsonValue]) -> ProviderConfig
```

_No docstring yet._

## class `HTTPProvider`

_No docstring yet._

### `__init__`

```python
def __init__(self, config: ProviderConfig, transport: httpx.BaseTransport | None=None)
```

_No docstring yet._

### `generate`

```python
def generate(self, system: str, user: str, schema: dict[str, JsonValue], max_tokens: int, timeout: float) -> ModelReply
```

_No docstring yet._

## Functions

### `load_environment`

```python
def load_environment(path: Path=Path('.env')) -> None
```

_No docstring yet._

### `redact`

```python
def redact(text: str) -> str
```

_No docstring yet._

### `strict_output_schema`

```python
def strict_output_schema(schema: dict[str, JsonValue]) -> dict[str, JsonValue]
```

Require explicit fields for strict chat endpoints; host validation stays unchanged.

Our optional proposal collections must be emitted as empty arrays, not omitted.
Return a new schema so adapting transport never mutates the host contract.
