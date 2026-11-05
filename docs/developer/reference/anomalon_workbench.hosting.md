# `anomalon_workbench.hosting`

Source: `src/anomalon_workbench/hosting.py`

Hosted admission boundary: verified OIDC claims, isolated stores, fixed provider.

## class `Principal` (Record)

_No docstring yet._

Fields:

- `owner: str`
- `expires: int`

## class `HostedPolicy` (Record)

_No docstring yet._

Fields:

- `live_enabled: bool`
- `auth_enabled: bool`
- `issuer: str`
- `subjects: tuple[str, ...]`
- `model: str`
- `daily_requests: int`
- `user_daily_requests: int`
- `daily_microdollars: int`
- `user_daily_microdollars: int`
- `request_microdollars: int`
- `concurrent_runs: int`

### `from_env`

```python
def from_env(cls) -> HostedPolicy
```

_No docstring yet._

### `login_subject`

```python
def login_subject(self, logged_in: bool, claims: Mapping[str, object]) -> str
```

Inspect Streamlit-verified identity without granting experiment authority.

### `authenticate`

```python
def authenticate(self, logged_in: bool, claims: Mapping[str, object]) -> Principal
```

Only call with claims verified by Streamlit OIDC, never uploaded JSON/headers.

### `provider`

```python
def provider(self) -> ProviderConfig
```

_No docstring yet._

### `permits`

```python
def permits(self, principal: Principal) -> bool
```

_No docstring yet._

## Functions

### `hosted_mode`

```python
def hosted_mode() -> bool
```

_No docstring yet._

### `secure_url`

```python
def secure_url(value: str) -> bool
```

_No docstring yet._

### `data_root`

```python
def data_root() -> Path
```

_No docstring yet._

### `private_store`

```python
def private_store(principal: Principal) -> Store
```

_No docstring yet._

### `submit_hosted`

```python
def submit_hosted(principal: Principal, spec: RunSpec, request_id: str) -> str
```

_No docstring yet._
