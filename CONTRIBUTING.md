# Contributing to nefin

Thanks for considering a contribution! This is a small, focused library — most
useful contributions are new/fixed loaders and bug reports about a dataset's
format changing.

## Setup

```bash
git clone https://github.com/nefin/nefin-python.git
cd nefin-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # test + excel + lint extras
pre-commit install         # runs ruff + mypy on every commit
```

## Before opening a PR

```bash
pytest        # tests + coverage (fails under 95%)
ruff check .
ruff format .
mypy
```

All four run in CI (see `.github/workflows/ci.yml`) and must pass.

## Adding or fixing a loader

Every `load_*` function follows the same shape — see `src/nefin/loaders.py`
for the existing ones (`load_risk_factors` and `load_cost_of_equity` are the
simplest references). In short:

1. Check the raw file's actual format first — fetch it directly
   (`curl https://nefin.com.br/nefindata/<folder>/<file>.csv`) rather than
   guessing from the [README](https://nefin.com.br/nefindata/README.md)'s
   description. NEFIN's raw files mix PT/EN headers, `,`/`;` separators, and
   different date layouts (`YYYY-MM-DD`, `M/YYYY`, split `year`/`month`/`day`
   columns) — don't assume consistency across datasets.
2. Add/update the dataset's entry in `src/nefin/registry.py`.
3. Write the loader in `src/nefin/loaders.py`: normalize columns to
   snake_case English, index the result by a `date` `DatetimeIndex`, and wrap
   it with `@_reraise_with_context` so failures surface as
   `NefinDownloadError`.
4. Export it from `src/nefin/__init__.py`.
5. Add tests in `tests/test_loaders.py` using mocked HTTP responses built
   from real sample content (don't invent a format — copy it from a `curl`
   of the actual file). Add error-path tests in `tests/test_error_handling.py`
   if the loader has any input validation (e.g. an unknown `sector`).
6. Update `CHANGELOG.md`'s `[Unreleased]` section and the README's API list.

## Reporting a dataset format change

If a loader starts failing because NEFIN changed a file's columns, separator,
or date format, please open an issue with:
- Which `load_*` function / dataset
- The error message (should be a `NefinDownloadError` naming the URL)
- What the raw file's header row looks like now (`curl` it)

## Release process (maintainers)

See the "Releasing to PyPI" section of [README.md](README.md#releasing-to-pypi).
