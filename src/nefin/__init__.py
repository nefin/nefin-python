"""nefin: pandas-ready loaders for NEFIN's public datasets (nefin.com.br)."""

from .core import NefinDownloadError, get_url, load_csv, load_excel
from .loaders import (
    load_cost_of_equity,
    load_dividend_yield,
    load_illiquidity_index,
    load_loan_fees,
    load_portfolios,
    load_risk_aversion,
    load_risk_factors,
    load_short_interest,
    load_spot_rate_curve,
    load_variance_premium,
    load_volatility_index,
)
from .registry import DATASETS

__version__ = "0.1.0"

__all__ = [
    "load_risk_factors",
    "load_cost_of_equity",
    "load_spot_rate_curve",
    "load_volatility_index",
    "load_risk_aversion",
    "load_variance_premium",
    "load_dividend_yield",
    "load_loan_fees",
    "load_portfolios",
    "load_short_interest",
    "load_illiquidity_index",
    "load_csv",
    "load_excel",
    "get_url",
    "DATASETS",
    "NefinDownloadError",
]
