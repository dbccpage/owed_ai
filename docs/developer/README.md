# Developer guide

## Layout

| Path | What it holds |
| --- | --- |
| `src/anomalon_workbench/` | The application package (Streamlit UI, checkers, migration engine, storage, providers) |
| `app.py` | Streamlit entry point |
| `tests/` | Pytest suite |
| `scripts/` | Validation, release and documentation scripts |
| `lean/` | Lean 4 models checked in CI |
| `fixtures/`, `examples/` | Inputs and retained attempts |
| `evidence/` | Validation receipts cited by the docs |
| `docs/` | This documentation |

## Checks (same as CI)

```powershell
uv sync --locked
uv run ruff check src tests scripts app.py
uv run mypy src
uv run pytest -q
uv run python scripts/check_lean.py
uv run python scripts/check_migration_lean.py
```

## Class-by-class reference

[reference/](reference/README.md) is generated from the source. After changing a
public class, method or function, run:

```powershell
uv run python scripts/build_reference.py
```

`pytest` fails when the reference is stale. Items marked "No docstring yet" are
the documentation still owed; adding the docstring and regenerating fixes them.
