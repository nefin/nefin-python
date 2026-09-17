"""Generic download/cache/parse core shared by every loader.

Design notes:
- NEFIN publishes static files with no auth and no rate limiting, so a plain
  ``requests.get`` is enough. We still cache to disk because the underlying
  files update at most weekly and researchers tend to re-run notebooks a lot.
- Caching is a plain mtime-based file cache under ``~/.cache/nefin``
  (override with the ``NEFIN_CACHE_DIR`` env var) rather than a dependency
  like requests-cache, to keep the install footprint small.
- Every failure mode (network error, HTTP error, unparseable file, missing
  optional dependency, corrupt cache entry) is caught and re-raised as
  ``NefinDownloadError`` with a message naming the URL/dataset and what to do
  about it, instead of surfacing a bare requests/pandas traceback.
"""

from __future__ import annotations

import io
import logging
import os
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger("nefin")

BASE_URL = "https://nefin.com.br/nefindata"
README_URL = "https://nefin.com.br/nefindata/README.md"

# Matches the "at most weekly" update cadence mentioned by NEFIN.
DEFAULT_CACHE_TTL_SECONDS = 7 * 24 * 3600

DEFAULT_TIMEOUT_SECONDS = 30

# Retries only cover genuinely transient failures (connection errors, timeouts,
# 5xx/429 responses) with exponential backoff — not 404s or other 4xx, which
# won't fix themselves on retry.
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 0.5

try:
    _VERSION = version("nefin")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled checkout
    _VERSION = "0.0.0"

# Identifies us to nefin.com.br (and lets them reach out if they'd rather we
# throttled/stopped) instead of showing up as an anonymous python-requests hit.
USER_AGENT = f"nefin-python/{_VERSION} (+https://github.com/nefin/nefin-python)"


class NefinDownloadError(RuntimeError):
    """Raised when a NEFIN file cannot be downloaded, cached, or parsed.

    Always carries a human-readable message naming the URL/dataset involved
    and a suggestion for how to fix or work around the problem.
    """


def cache_dir() -> Path:
    """Root cache directory, re-read on every call so env overrides (e.g. in tests) apply."""
    return Path(os.environ.get("NEFIN_CACHE_DIR", Path.home() / ".cache" / "nefin"))


def get_url(datafolder: str, filename: str, ext: str = "csv") -> str:
    """Build the canonical download URL for a NEFIN file.

    >>> get_url("risk-factors", "nefin_factors")
    'https://nefin.com.br/nefindata/risk-factors/nefin_factors.csv'
    """
    return f"{BASE_URL}/{datafolder}/{filename}.{ext}"


def _cache_path(datafolder: str, filename: str, ext: str) -> Path:
    return cache_dir() / datafolder / f"{filename}.{ext}"


def _is_retryable_http_error(exc: requests.exceptions.HTTPError) -> bool:
    status = exc.response.status_code if exc.response is not None else None
    return status is not None and (status >= 500 or status == 429)


def _get_with_retries(url: str, *, timeout: float) -> requests.Response:
    """GET with exponential-backoff retries on transient failures.

    Non-transient failures (404s, other 4xx, malformed URLs, etc.) are
    re-raised immediately on the first attempt — retrying those would just
    waste time before _download_bytes turns them into a NefinDownloadError.
    """
    attempt = 0
    while True:
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            if attempt > 0:
                logger.debug("Succeeded on retry %d/%d for %s", attempt, _MAX_RETRIES, url)
            return response
        except requests.exceptions.HTTPError as exc:
            if attempt >= _MAX_RETRIES or not _is_retryable_http_error(exc):
                raise
            reason = f"HTTP {exc.response.status_code if exc.response is not None else '?'}"
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            if attempt >= _MAX_RETRIES:
                raise
            reason = str(exc)
        wait = _BACKOFF_BASE_SECONDS * (2**attempt)
        logger.debug(
            "Retrying %s after %s (attempt %d/%d, backing off %.1fs)",
            url,
            reason,
            attempt + 1,
            _MAX_RETRIES,
            wait,
        )
        time.sleep(wait)
        attempt += 1


def _download_bytes(
    datafolder: str,
    filename: str,
    ext: str,
    *,
    use_cache: bool = True,
    ttl: float = DEFAULT_CACHE_TTL_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bytes:
    """Fetch raw file bytes, transparently serving from the local cache when fresh."""
    url = get_url(datafolder, filename, ext)
    path = _cache_path(datafolder, filename, ext)

    if use_cache and path.exists():
        try:
            age = time.time() - path.stat().st_mtime
            if age < ttl:
                logger.debug("Cache hit for %s (age %.0fs < ttl %.0fs)", url, age, ttl)
                return path.read_bytes()
            logger.debug("Cache stale for %s (age %.0fs >= ttl %.0fs)", url, age, ttl)
        except OSError as exc:
            raise NefinDownloadError(
                f"Could not read cached file {path}: {exc}. "
                f"Delete it manually or call the loader with use_cache=False to re-download."
            ) from exc

    logger.debug("Downloading %s", url)
    try:
        response = _get_with_retries(url, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise NefinDownloadError(
            f"Timed out downloading {url} after {timeout}s (retried {_MAX_RETRIES} times). "
            f"nefin.com.br may be slow or unreachable right now — try again later, "
            f"or pass a larger timeout=."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        retried_note = (
            f" (retried {_MAX_RETRIES} times)" if _is_retryable_http_error(exc) else ""
        )
        raise NefinDownloadError(
            f"NEFIN returned HTTP {status} for {url}{retried_note}. "
            f"The file may have been renamed or removed — check {README_URL} "
            f"for the current file list."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise NefinDownloadError(
            f"Could not download {url} (retried {_MAX_RETRIES} times): {exc}. "
            f"Check your network connection and that nefin.com.br is reachable."
        ) from exc

    content = response.content

    if use_cache:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            logger.debug("Cached %s to %s", url, path)
        except OSError as exc:
            raise NefinDownloadError(
                f"Downloaded {url} but could not write it to the cache at {path}: {exc}. "
                f"Check permissions on {cache_dir()}, set NEFIN_CACHE_DIR to a writable "
                f"directory, or pass use_cache=False."
            ) from exc

    return content


def load_csv(
    datafolder: str,
    filename: str,
    *,
    use_cache: bool = True,
    ttl: float = DEFAULT_CACHE_TTL_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    **read_csv_kwargs: Any,
) -> pd.DataFrame:
    """Download (or read from cache) a NEFIN CSV file as a raw DataFrame.

    This is the escape hatch for datasets not yet wrapped by a dedicated
    ``load_*`` function — no column renaming or date parsing is applied
    beyond whatever ``read_csv_kwargs`` you pass through to ``pandas.read_csv``.
    """
    url = get_url(datafolder, filename, "csv")
    content = _download_bytes(
        datafolder, filename, "csv", use_cache=use_cache, ttl=ttl, timeout=timeout
    )
    try:
        df: pd.DataFrame = pd.read_csv(io.BytesIO(content), **read_csv_kwargs)
        return df
    except Exception as exc:
        raise NefinDownloadError(
            f"Downloaded {url} but could not parse it as CSV: {exc}. "
            f"The file's format may have changed — check {README_URL}."
        ) from exc


def load_excel(
    datafolder: str,
    filename: str,
    *,
    use_cache: bool = True,
    ttl: float = DEFAULT_CACHE_TTL_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    **read_excel_kwargs: Any,
) -> pd.DataFrame:
    """Download (or read from cache) a NEFIN XLS/XLSX file as a raw DataFrame.

    Requires the ``excel`` extra (``xlrd`` for legacy ``.xls``, ``openpyxl``
    for ``.xlsx``) — install with ``pip install nefin[excel]``.
    """
    ext = "xls"
    url = get_url(datafolder, filename, ext)
    content = _download_bytes(
        datafolder, filename, ext, use_cache=use_cache, ttl=ttl, timeout=timeout
    )
    try:
        df: pd.DataFrame = pd.read_excel(io.BytesIO(content), **read_excel_kwargs)
        return df
    except ImportError as exc:
        raise NefinDownloadError(
            f"Downloaded {url} but no Excel engine is installed to read it: {exc}. "
            f"Install one with `pip install nefin[excel]` (adds xlrd + openpyxl)."
        ) from exc
    except Exception as exc:
        raise NefinDownloadError(
            f"Downloaded {url} but could not parse it as an Excel file: {exc}. "
            f"The file's format may have changed — check {README_URL}."
        ) from exc
