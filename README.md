# nefin

[![PyPI](https://img.shields.io/pypi/v/nefin.svg)](https://pypi.org/project/nefin/)
[![Python versions](https://img.shields.io/pypi/pyversions/nefin.svg)](https://pypi.org/project/nefin/)
[![CI](https://github.com/nefin/nefin-python/actions/workflows/ci.yml/badge.svg)](https://github.com/nefin/nefin-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pandas-ready loaders for [NEFIN](https://nefin.com.br/nefindata/README.md)'s public
finance datasets, so you can write:

```python
import nefin as nd

df = nd.load_risk_factors()
consumer = nd.load_cost_of_equity(sector="consumer")
```

instead of manually downloading CSVs/XLS from nefin.com.br and wrangling them into shape.

## Install

```bash
pip install nefin
# datasets that are XLS-only (portfolios, risk-aversion, variance-premium) need:
pip install "nefin[excel]"
```

## API

```python
nd.load_risk_factors()
nd.load_cost_of_equity(sector="consumer")  # or sector=None -> dict[str, DataFrame]
nd.load_spot_rate_curve()
nd.load_volatility_index()  # ivol_br
nd.load_risk_aversion()  # requires nefin[excel]
nd.load_variance_premium()  # requires nefin[excel]
nd.load_dividend_yield()
nd.load_loan_fees()
nd.load_portfolios(sort_by="size", n=3)  # requires nefin[excel]
nd.load_short_interest(metric="short_interest")  # metric="all" -> merged on date
nd.load_illiquidity_index()  # raises NotImplementedError: not yet published by NEFIN

# escape hatch for anything not yet wrapped
nd.load_csv("risk-factors", "nefin_factors")
nd.get_url("cost-of-equity", "consumer", ext="csv")
```

Every loader returns a `DataFrame` indexed by a `date` `DatetimeIndex`, with
snake_case English column names regardless of the raw file's PT/EN headers.

## Caching

Downloads are cached to `~/.cache/nefin` (override with `NEFIN_CACHE_DIR`) for
one week by default, since NEFIN updates its files at most weekly. Pass
`use_cache=False` to any loader to force a fresh download.

## Logging

`nefin` logs cache hits/misses, downloads, and retries at `DEBUG` under the
`"nefin"` logger. It's silent by default (no handlers attached), following
standard library practice — opt in with:

```python
import logging

logging.getLogger("nefin").setLevel(logging.DEBUG)
logging.basicConfig()
```

## Error handling

Every failure — a network error, an HTTP error, a changed file format, a
missing `xlrd`/`openpyxl` engine — is raised as `nefin.NefinDownloadError`
with a message naming the URL/dataset involved and what to do about it,
instead of a bare `requests`/`pandas` traceback. Bad arguments (unknown
`sector`, `metric`, `sort_by`) raise a plain `ValueError`.

Transient failures (connection errors, timeouts, 5xx/429 responses) are
retried automatically with exponential backoff (up to 3 retries) before
raising. Non-transient failures like 404s fail immediately.

## Development

```bash
pip install -e ".[dev]"  # test + excel + lint extras
pytest               # runs with coverage on by default (fails under 95%)
ruff check .        # lint
ruff format .       # format
mypy                # static type check (strict mode)
pre-commit install  # run ruff + mypy automatically on every commit
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow, including how
to add a new dataset loader.

## Citing

If `nefin` was useful in academic work, please cite it — see
[CITATION.cff](CITATION.cff) (GitHub's "Cite this repository" button on this
repo generates APA/BibTeX from it). Also cite NEFIN's own methodology for
the underlying data: https://nefin.com.br/nefindata/README.md.

## Releasing to PyPI

Publishing runs via `.github/workflows/publish.yml` using
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC —
no API tokens stored as secrets). One-time setup, per environment
(`pypi` and, optionally, `testpypi`):

1. On [pypi.org](https://pypi.org/manage/account/publishing/) (and
   [test.pypi.org](https://test.pypi.org/manage/account/publishing/) for the
   test environment), add a new trusted publisher pointing at this repo,
   workflow file `publish.yml`, and environment name `pypi` (or `testpypi`).
2. In the GitHub repo settings, create matching `pypi` / `testpypi`
   [environments](https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment).

To release: move the `[Unreleased]` section of [CHANGELOG.md](CHANGELOG.md)
under a new `## [X.Y.Z] - YYYY-MM-DD` heading, bump `__version__` in
`src/nefin/__init__.py` to match, then publish a GitHub Release with a
matching tag (e.g. `v0.2.0`) — this triggers `publish-pypi`. To dry-run
against TestPyPI first, run the workflow manually from the Actions tab with
`target: testpypi`.
