"""Hardcoded catalog of NEFIN datasets.

Source of truth for this snapshot: https://nefin.com.br/nefindata/README.md
Pin date: 2026-09-14. If the site's file list or naming drifts, update this
registry accordingly rather than scraping the README at runtime — there are
only a handful of datasets and they change rarely.
"""

from __future__ import annotations

from typing import Literal

# Keep these Literal aliases in sync with the tuples/dicts below by hand —
# mypy can't derive a Literal from a runtime collection, so this is the
# closest we get to a single source of truth for the valid string values.
CostOfEquitySector = Literal[
    "basic_products",
    "construction",
    "consumer",
    "energy",
    "finance",
    "manufacturing",
    "other",
]

PortfolioSortBy = Literal["size", "book_to_market", "momentum", "illiquidity", "industry"]

PortfolioWeighting = Literal[
    "equal", "value", "n_stocks", "market_value", "book_value", "book_to_market"
]

ShortInterestMetric = Literal["short_interest", "days_to_cover", "loan_fee"]

COST_OF_EQUITY_SECTORS: tuple[CostOfEquitySector, ...] = (
    "basic_products",
    "construction",
    "consumer",
    "energy",
    "finance",
    "manufacturing",
    "other",
)

PORTFOLIO_SORTS: dict[PortfolioSortBy, dict[str, tuple[int, ...]]] = {
    "size": {"n": (3,)},
    "book_to_market": {"n": (3, 4)},
    "momentum": {"n": (3, 4)},
    "illiquidity": {"n": (3, 4)},
    "industry": {"n": (7,)},
}

SHORT_INTEREST_METRICS: dict[ShortInterestMetric, str] = {
    "short_interest": "average_short_interest",
    "days_to_cover": "average_days_to_cover",
    "loan_fee": "average_loan_fee",
}

# datafolder -> metadata. `files` maps filename -> tuple of available extensions,
# preferring csv first where both exist.
DATASETS = {
    "risk-factors": {
        "description": "Daily risk factors and risk-free rate (NEFIN's flagship dataset)",
        "frequency": "daily",
        "coverage": "2001-01-02 -> present",
        "files": {"nefin_factors": ("csv",)},
    },
    "cost-of-equity": {
        "description": "Monthly implied cost of equity by sector",
        "frequency": "monthly",
        "coverage": "2005-01 -> 2023-08",
        "files": {sector: ("csv", "xls") for sector in COST_OF_EQUITY_SECTORS},
    },
    "spot-rate-curve": {
        "description": "Zero-coupon spot rate curve",
        "frequency": "daily",
        "coverage": "2002-01-02 -> 2020-05",
        "files": {"spot_rate_curve": ("csv", "xls")},
    },
    "volatility-index": {
        "description": "Implied volatility index, risk aversion, and variance premium",
        "frequency": "daily",
        "coverage": "2011-08 -> 2022-04",
        "files": {
            "ivol_br": ("csv", "xls"),
            "risk_aversion": ("xls",),
            "variance_premium": ("xls",),
        },
    },
    "dividend-yield": {
        "description": "Weekly market dividend yield (as a fraction, not percent)",
        "frequency": "weekly",
        "coverage": "2001-02 -> 2023-09",
        "files": {"dividend_yield": ("csv", "xls")},
    },
    "loan-fees": {
        "description": "Weekly average stock loan fees",
        "frequency": "weekly",
        "coverage": "2013-01 -> 2023-09",
        "files": {"loan_fees": ("csv", "xls")},
    },
    "portfolios": {
        "description": "Sorted equity portfolios (XLS only, no CSV published)",
        "frequency": "daily",
        "coverage": "2001-01 -> 2023-08",
        "files": {
            "3_portfolios_sorted_by_size": ("xls",),
            "3_portfolios_sorted_by_book_to_market": ("xls",),
            "3_portfolios_sorted_by_momentum": ("xls",),
            "3_portfolios_sorted_by_illiquidity": ("xls",),
            "4_portfolios_sorted_by_size_and_book_to_market_2x2": ("xls",),
            "4_portfolios_sorted_by_size_and_illiquidity_2x2": ("xls",),
            "4_portfolios_sorted_by_size_and_momentum_2x2": ("xls",),
            "7_portfolios_sorted_by_industry": ("xls",),
        },
    },
    "short-interest": {
        "description": "Daily average short interest, days to cover, and loan fee",
        "frequency": "daily",
        "coverage": "2012-11 -> present",
        "files": {name: ("csv",) for name in SHORT_INTEREST_METRICS.values()},
    },
    "illiquidity-index": {
        "description": "No file published yet on nefin.com.br",
        "frequency": None,
        "coverage": None,
        "files": {},
    },
    "methodology": {
        "description": "Shared methodology PDF (not tabular)",
        "frequency": None,
        "coverage": None,
        "files": {"nefin_methodology": ("pdf",)},
    },
}
