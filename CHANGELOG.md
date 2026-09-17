# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `ruff` for linting and formatting, wired into CI and `pre-commit`.
- `mypy --strict` type checking, wired into CI and `pre-commit`. Public API
  parameters (`sector`, `sort_by`, `weighting`, `metric`) are now `Literal`
  types for IDE autocomplete and static validation.
- Branch coverage enforced at 95%+ (`pytest-cov`, `--cov-fail-under=95`),
  currently at 100%. New tests cover every error-handling branch in
  `core.py` (cache I/O failures, missing Excel engine) and `loaders.py`
  (schema-drift wrapping, all `load_portfolios`/`load_short_interest`
  branches).
- Requests now send an identifying `User-Agent`
  (`nefin-python/<version> (+https://github.com/nefin/nefin-python)`)
  instead of showing up as an anonymous `python-requests` hit against
  nefin.com.br.
- Automatic retry with exponential backoff (up to 3 retries) on transient
  network failures — connection errors, timeouts, and 5xx/429 responses.
  Non-transient failures (404s, other 4xx) fail immediately without
  retrying.
- Debug logging under the `"nefin"` logger for cache hits/misses, downloads,
  cache writes, and retries. Silent by default (no handlers attached).
- `CONTRIBUTING.md`, GitHub issue templates (bug report / feature request),
  and a PR template. `CHANGELOG.md`/`CONTRIBUTING.md` are now included in
  the sdist.

## [0.1.0] - 2026-09-17

### Added
- Generic download/cache core (`load_csv`, `load_excel`, `get_url`) with a
  local file cache at `~/.cache/nefin` (override with `NEFIN_CACHE_DIR`).
- `NefinDownloadError` wrapping network, HTTP, cache, and parsing failures
  with actionable messages.
- Loaders for every published NEFIN dataset: `load_risk_factors`,
  `load_cost_of_equity`, `load_spot_rate_curve`, `load_volatility_index`,
  `load_risk_aversion`, `load_variance_premium`, `load_dividend_yield`,
  `load_loan_fees`, `load_portfolios`, `load_short_interest`.
  `load_illiquidity_index` raises `NotImplementedError` since NEFIN has not
  published that file yet.
- PyPI packaging (dynamic versioning, classifiers, `py.typed`) and GitHub
  Actions for CI and Trusted-Publishing-based PyPI releases.

[Unreleased]: https://github.com/nefin/nefin-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nefin/nefin-python/releases/tag/v0.1.0
