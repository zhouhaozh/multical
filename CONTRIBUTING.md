# Contributing

## Development setup

Multical supports Python 3.10 through 3.12. Create an isolated environment and
install the development extras:

```bash
python -m pip install -e ".[dev]"
```

Run the same checks used by continuous integration before opening a pull
request:

```bash
python -m ruff check .
python -m pytest
python -m pip wheel --no-deps --wheel-dir dist .
```

## Repository policy

- Keep `origin` pointed at the personal fork and `upstream` pointed at the
  original project.
- Develop on topic branches and merge them through pull requests. Never force
  push `master`.
- Do not commit camera datasets, generated calibration results, caches, local
  virtual environments, credentials, or machine-specific paths.
- Keep fixtures small, deterministic, anonymous, and directly tied to an
  automated test.
- Preserve command-line arguments and serialized calibration formats unless a
  change includes a compatibility layer and migration notes.

## Commits

Commit messages use the repository's Lore protocol: start with the intent, then
record relevant constraints, rejected alternatives, confidence, scope risk,
verification, and known gaps as Git trailers.
