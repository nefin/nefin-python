"""Dataset-specific loaders.

Each ``load_*`` function normalizes the raw file (mixed PT/EN headers, mixed
date formats, ``,`` vs ``;`` separators, split year/month/day columns) into a
single consistent snake_case English schema, indexed by a ``DatetimeIndex``
named ``date``.

Every loader is wrapped so that any failure — a network error, an HTTP error,
a changed file format, a missing optional dependency (xlrd/openpyxl) — is
raised as :class:`nefin.core.NefinDownloadError` with a message naming
the loader and the dataset involved, instead of a bare traceback from
``requests``/``pandas``.
"""

from __future__ import annotations

import re
from functools import wraps

import pandas as pd

from . import core
from .core import README_URL, NefinDownloadError
from .registry import COST_OF_EQUITY_SECTORS, PORTFOLIO_SORTS, SHORT_INTEREST_METRICS


def _reraise_with_context(func):
    """Wrap a loader so any unexpected failure is a clear NefinDownloadError."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NefinDownloadError:
            raise
        except (ValueError, TypeError):
            # Let intentional input-validation errors (bad sector/metric/sort_by)
            # pass through unchanged — they are not download/parse failures.
            raise
        except Exception as exc:
            raise NefinDownloadError(
                f"{func.__name__}() failed while processing NEFIN data: {exc}. "
                f"The raw file's format may have changed — check {README_URL}."
            ) from exc

    return wrapper


def _ymd_to_date(
    df: pd.DataFrame, *, year="year", month="month", day="day"
) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(dict(year=df[year], month=df[month], day=df[day])))


# ---------------------------------------------------------------------------
# risk-factors
# ---------------------------------------------------------------------------

_RISK_FACTORS_COLUMNS = {
    "Date": "date",
    "Rm_minus_Rf": "rm_minus_rf",
    "SMB": "smb",
    "HML": "hml",
    "WML": "wml",
    "IML": "iml",
    "Risk_Free": "risk_free",
}


@_reraise_with_context
def load_risk_factors(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's daily risk factors and risk-free rate.

    Returns a DataFrame indexed by date with columns:
    ``rm_minus_rf``, ``smb``, ``hml``, ``wml``, ``iml``, ``risk_free``.
    """
    raw = core.load_csv(
        "risk-factors",
        "nefin_factors",
        use_cache=use_cache,
        index_col=0,
    )
    df = raw.rename(columns=_RISK_FACTORS_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


# ---------------------------------------------------------------------------
# cost-of-equity
# ---------------------------------------------------------------------------

_COST_OF_EQUITY_HORIZON_RE = re.compile(r"custo_capital_(\d+)anos?_\d+")


def _parse_month_year(series: pd.Series) -> pd.DatetimeIndex:
    """Parse NEFIN's "M/YYYY" strings (e.g. "1/2005") into month-start timestamps."""
    parts = series.str.split("/", expand=True)
    month = parts[0].astype(int)
    year = parts[1].astype(int)
    return pd.DatetimeIndex(pd.to_datetime(dict(year=year, month=month, day=1)))


def _rename_cost_of_equity_columns(columns: pd.Index) -> dict:
    renamed = {}
    for col in columns:
        match = _COST_OF_EQUITY_HORIZON_RE.match(col)
        if match:
            renamed[col] = f"horizon_{match.group(1)}y"
    return renamed


def _load_cost_of_equity_sector(sector: str, *, use_cache: bool) -> pd.DataFrame:
    raw = core.load_csv(
        "cost-of-equity",
        sector,
        use_cache=use_cache,
        sep=";",
        dtype={"data_mes_ano": str},
    )
    df = raw.rename(columns=_rename_cost_of_equity_columns(raw.columns))
    df["date"] = _parse_month_year(raw["data_mes_ano"])
    df = df.drop(columns=["data_mes_ano"])
    return df.set_index("date").sort_index()


@_reraise_with_context
def load_cost_of_equity(
    sector: str | None = None, *, use_cache: bool = True
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load NEFIN's monthly implied cost of equity by sector.

    Values are annualized rates in percent (e.g. ``16.32`` means 16.32%/yr),
    for horizons of 1/5/10/20 years (columns ``horizon_1y`` ... ``horizon_20y``).

    Parameters
    ----------
    sector:
        One of ``nefin.registry.COST_OF_EQUITY_SECTORS``. If ``None``,
        returns a ``dict`` of ``{sector: DataFrame}`` for every sector.
    """
    if sector is None:
        return {
            s: _load_cost_of_equity_sector(s, use_cache=use_cache)
            for s in COST_OF_EQUITY_SECTORS
        }
    if sector not in COST_OF_EQUITY_SECTORS:
        raise ValueError(
            f"Unknown sector {sector!r}. Expected one of {COST_OF_EQUITY_SECTORS}."
        )
    return _load_cost_of_equity_sector(sector, use_cache=use_cache)


# ---------------------------------------------------------------------------
# spot-rate-curve
# ---------------------------------------------------------------------------

_SPOT_RATE_COLUMNS = {
    "Date": "date",
    "1 month": "maturity_1m",
    "2 months": "maturity_2m",
    "3 months": "maturity_3m",
    "6 months": "maturity_6m",
    "1 year": "maturity_1y",
    "3 years": "maturity_3y",
    "5 years": "maturity_5y",
}


@_reraise_with_context
def load_spot_rate_curve(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's daily zero-coupon spot rate curve.

    Returns a DataFrame indexed by date with columns
    ``maturity_1m, maturity_2m, maturity_3m, maturity_6m, maturity_1y,
    maturity_3y, maturity_5y``.
    """
    raw = core.load_csv("spot-rate-curve", "spot_rate_curve", use_cache=use_cache, index_col=0)
    df = raw.rename(columns=_SPOT_RATE_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


# ---------------------------------------------------------------------------
# volatility-index / risk-aversion / variance-premium
# ---------------------------------------------------------------------------


@_reraise_with_context
def load_volatility_index(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's daily implied volatility index (IVol-BR).

    Returns a DataFrame indexed by date with a single column ``ivol_br``.
    """
    raw = core.load_csv("volatility-index", "ivol_br", use_cache=use_cache)
    df = raw.rename(columns={"ivolbr": "ivol_br"})
    df["date"] = _ymd_to_date(raw)
    return df[["date", "ivol_br"]].set_index("date").sort_index()


@_reraise_with_context
def load_risk_aversion(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's daily risk aversion index (XLS-only, requires the ``excel`` extra).

    Returns a DataFrame indexed by date with a single column ``risk_aversion``.
    """
    raw = core.load_excel("volatility-index", "risk_aversion", use_cache=use_cache)
    df = raw.copy()
    df["date"] = _ymd_to_date(raw)
    return df[["date", "risk_aversion"]].set_index("date").sort_index()


@_reraise_with_context
def load_variance_premium(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's daily variance premium (XLS-only, requires the ``excel`` extra).

    Returns a DataFrame indexed by date with a single column ``variance_premium``.
    """
    raw = core.load_excel("volatility-index", "variance_premium", use_cache=use_cache)
    df = raw.rename(columns={"premium": "variance_premium"})
    df["date"] = _ymd_to_date(raw)
    return df[["date", "variance_premium"]].set_index("date").sort_index()


# ---------------------------------------------------------------------------
# dividend-yield / loan-fees (weekly, ano/mes/dia layout)
# ---------------------------------------------------------------------------


@_reraise_with_context
def load_dividend_yield(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's weekly market dividend yield.

    Returns a DataFrame indexed by date with a single column
    ``dividend_yield`` expressed as a fraction (not percent).
    """
    raw = core.load_csv("dividend-yield", "dividend_yield", use_cache=use_cache)
    df = raw.rename(columns={"yield_week_pc": "dividend_yield"})
    df["date"] = _ymd_to_date(raw, year="ano", month="mes", day="dia")
    return df[["date", "dividend_yield"]].set_index("date").sort_index()


@_reraise_with_context
def load_loan_fees(*, use_cache: bool = True) -> pd.DataFrame:
    """Load NEFIN's weekly average stock loan fees.

    Returns a DataFrame indexed by date with a single column ``loan_fee``.
    """
    raw = core.load_csv("loan-fees", "loan_fees", use_cache=use_cache)
    df = raw.rename(columns={"semana_aluguel_100": "loan_fee"})
    df["date"] = _ymd_to_date(raw, year="ano", month="mes", day="dia")
    return df[["date", "loan_fee"]].set_index("date").sort_index()


# ---------------------------------------------------------------------------
# portfolios (XLS only, multi-sheet)
# ---------------------------------------------------------------------------

_PORTFOLIO_SHEETS = {
    "equal": "Equally Weighted Returns",
    "value": "Value Weighted Returns",
    "n_stocks": "Number of stocks",
    "market_value": "Average market value",
    "book_value": "Average book value",
    "book_to_market": "Average book-to-market ratio",
}

_SNAKE_CASE_BOUNDARY_RE = re.compile(r"(?<=[A-Za-z])(?=[0-9])")


def _portfolio_filename(sort_by: str, n: int) -> str:
    if sort_by not in PORTFOLIO_SORTS:
        raise ValueError(
            f"Unknown sort_by {sort_by!r}. Expected one of {sorted(PORTFOLIO_SORTS)}."
        )
    valid_n = PORTFOLIO_SORTS[sort_by]["n"]
    if n not in valid_n:
        raise ValueError(
            f"n={n} is not available for sort_by={sort_by!r}. Expected one of {valid_n}."
        )
    if sort_by == "industry":
        return "7_portfolios_sorted_by_industry"
    if sort_by == "size":
        return "3_portfolios_sorted_by_size"
    if n == 3:
        return f"3_portfolios_sorted_by_{sort_by}"
    return f"4_portfolios_sorted_by_size_and_{sort_by}_2x2"


def _snake_case_portfolio_column(col: str) -> str:
    return _SNAKE_CASE_BOUNDARY_RE.sub("_", col).lower()


@_reraise_with_context
def load_portfolios(
    *, sort_by: str = "size", n: int = 3, weighting: str = "equal", use_cache: bool = True
) -> pd.DataFrame:
    """Load NEFIN's sorted equity portfolios (XLS-only, requires the ``excel`` extra).

    Parameters
    ----------
    sort_by:
        One of ``"size"``, ``"book_to_market"``, ``"momentum"``, ``"illiquidity"``,
        ``"industry"``. See ``nefin.registry.PORTFOLIO_SORTS`` for which
        ``n`` values are valid for each.
    n:
        Number of portfolios (3, 4, or 7 depending on ``sort_by``).
    weighting:
        Which sheet to read: ``"equal"`` (default), ``"value"``, ``"n_stocks"``,
        ``"market_value"``, ``"book_value"``, or ``"book_to_market"`` (the last
        only meaningful as a diagnostic, not a return series).

    Returns a DataFrame indexed by date with one column per portfolio.
    """
    filename = _portfolio_filename(sort_by, n)
    if weighting not in _PORTFOLIO_SHEETS:
        raise ValueError(
            f"Unknown weighting {weighting!r}. Expected one of {sorted(_PORTFOLIO_SHEETS)}."
        )
    raw = core.load_excel(
        "portfolios", filename, use_cache=use_cache, sheet_name=_PORTFOLIO_SHEETS[weighting]
    )
    df = raw.rename(columns=_snake_case_portfolio_column)
    df["date"] = _ymd_to_date(raw)
    value_cols = [c for c in df.columns if c not in ("year", "month", "day", "date")]
    return df[["date", *value_cols]].set_index("date").sort_index()


# ---------------------------------------------------------------------------
# short-interest
# ---------------------------------------------------------------------------


def _load_short_interest_metric(metric: str, *, use_cache: bool) -> pd.DataFrame:
    filename = SHORT_INTEREST_METRICS[metric]
    raw = core.load_csv("short-interest", filename, use_cache=use_cache)
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


@_reraise_with_context
def load_short_interest(
    *, metric: str = "short_interest", use_cache: bool = True
) -> pd.DataFrame:
    """Load NEFIN's daily average short-interest metrics.

    Parameters
    ----------
    metric:
        One of ``"short_interest"``, ``"days_to_cover"``, ``"loan_fee"``, or
        ``"all"`` to merge all three (outer join) into one DataFrame indexed
        by date, columns ``average_short_interest``, ``average_days_to_cover``,
        ``average_loan_fee``.
    """
    if metric == "all":
        frames = [
            _load_short_interest_metric(m, use_cache=use_cache) for m in SHORT_INTEREST_METRICS
        ]
        merged = frames[0]
        for frame in frames[1:]:
            merged = merged.join(frame, how="outer")
        return merged.sort_index()
    if metric not in SHORT_INTEREST_METRICS:
        raise ValueError(
            f"Unknown metric {metric!r}. Expected one of "
            f"{sorted(SHORT_INTEREST_METRICS)} or 'all'."
        )
    return _load_short_interest_metric(metric, use_cache=use_cache)


# ---------------------------------------------------------------------------
# illiquidity-index (not published)
# ---------------------------------------------------------------------------


def load_illiquidity_index(*, use_cache: bool = True) -> pd.DataFrame:
    raise NotImplementedError(
        "NEFIN has not published an illiquidity-index file yet. "
        f"Check {README_URL} for updates."
    )
