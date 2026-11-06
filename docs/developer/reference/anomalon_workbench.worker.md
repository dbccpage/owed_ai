# `anomalon_workbench.worker`

Source: `src/anomalon_workbench/worker.py`

A separate bounded worker; reruns cannot claim an already-running job.

## Functions

### `launch`

```python
def launch(store: Store, run_id: str) -> subprocess.Popen[bytes]
```

_No docstring yet._

### `work`

```python
def work(root: Path, run_id: str) -> None
```

_No docstring yet._
