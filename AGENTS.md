# dy

Minimal Python 3.12+ project. No dependencies yet.

## Commands

```bash
# run the project (once main module exists)
python -m dy

# activate venv
source .venv/bin/activate
```

## Conventions

- Virtualenv lives at `.venv/` (gitignored). It's a symlink to the system Python — recreate with `python3 -m venv .venv` when adding deps.
- PyCharm project files in `.idea/` are gitignored.
- No test runner, linter, or type checker installed yet. The `.venv` mirrors the system interpreter.
- `pyproject.toml` is the single source of truth for metadata and dependencies.
