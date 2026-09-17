# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `ruff` for linting and formatting, wired into CI and `pre-commit`.

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
