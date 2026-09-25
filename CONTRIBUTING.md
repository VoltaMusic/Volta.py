# Contributing to VoltaLib

Thanks for helping out! This page covers everything you need to work on the library: setup, checks, conventions and how a release goes out.

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/VoltaMusic/Volta.py.git
cd Volta.py
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # the package + pytest, ruff, mypy, pre-commit, build
pre-commit install               # run ruff and mypy before each commit
```

The tests never call the real API, so you don't need Volta credentials to work on the library. To try your changes against the real API, create a `.env` file at the project root (see the README's **Config** section). It is ignored by git.

## Checks

The CI runs these three commands on Python 3.10, 3.11, 3.12 and 3.13. Run them before opening a pull request:

```bash
ruff check .     # lint (ruff check . --fix fixes most issues)
mypy             # type check
pytest           # tests (add --cov=VoltaLibPython for coverage)
```

To run them on every supported Python version at once, like the CI, use `scripts/test_matrix.sh` (Linux, macOS, Git Bash) or `scripts\test_matrix.bat` (Windows). Both need [uv](https://docs.astral.sh/uv/).

## Project layout

```
VoltaLibPython/
├── client.py              # VoltaClient: token handling, HTTP requests, 401 retry
├── session.py             # requests session and retry policy (GET and token only)
├── exceptions.py          # every exception, and error_from_response()
├── progress.py            # optional loading spinner
└── endpoints/
    ├── _base.py           # _Endpoint base class and _path()
    ├── verbs.py           # client.get / post / put / delete namespaces
    ├── catalog.py         # client.get.catalog
    ├── library.py         # client.get.library
    └── library_write.py   # client.post / put / delete .library
tests/                     # one file per concern, see the README
docs/                      # one reference page per HTTP verb
```

## Adding an endpoint

1. Add a method to the matching class in `VoltaLibPython/endpoints/`. Build the route with `self._path(...)`, which encodes every segment, and never with an f-string. That way an ID can never change the route that is called.
2. Write a docstring with what the method does, its arguments and the API scope it needs (`Scope: library:write`).
3. Validate arguments before any network call and raise `InvalidArgumentError` when they are wrong.
4. Add tests with the `make_client` and `fake_session` fixtures from `tests/conftest.py`, including the encoded URL and the 401 retry.
5. Document the method in the matching `docs/*.md` page.

## Conventions

- **Language**: everything a user sees is in English (error messages, logs, docstrings, docs). Code comments can be in French.
- **Errors**: never let a raw `requests`, `json` or `OSError` exception escape. Convert it to one of the exceptions in `exceptions.py` and keep the original as `__cause__` (`raise ... from e`).
- **Writes are never retried**: a POST, PUT or DELETE can be processed by the server even when it answers 5xx, so retrying could create duplicates. Only GET and the token request are retried (see `session.py`).
- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `chore:`, `perf:`, `build:`. Make one commit per change.
- **Changelog**: add a line under `## Unreleased` in `changelog.md` for every change a user or a contributor would notice (`+` added, `~` changed or fixed, `-` removed).

## Releasing

1. Create a `release/x.y.z` branch from `main`.
2. Bump the version in `pyproject.toml` and in the README's wheel file name (`dist/voltalib-x.y.z-py3-none-any.whl`).
3. In `changelog.md`, rename `## Unreleased` to `## Ver x.y.z - <date>` and start a new empty `## Unreleased` section above it.
4. Commit (`chore: Bump version to x.y.z`), push and open a pull request to `main`.
5. Once it's merged, publish a GitHub release tagged `x.y.z` (no `v` prefix, like the existing tags). The **Upload Python Package** workflow builds the package and publishes it to PyPI.
