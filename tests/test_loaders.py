import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import nefin as nd
from nefin.registry import COST_OF_EQUITY_SECTORS

RISK_FACTORS_CSV = b"""\
"","Date","Rm_minus_Rf","SMB","HML","WML","IML","Risk_Free"
"1",2001-01-02,0.00660063299326548,0.115836998553672,0.0601153507912085,-0.00491699156244864,0.00787837722397337,0.000578516538294771
"2",2001-01-03,0.0624274996096267,0.0383097794477492,0.00844817019052758,-0.03709321416758,0.018070335041524,0.00057714347804283
"""

COST_OF_EQUITY_CSV = b"""\
data_mes_ano;custo_capital_1ano_1;custo_capital_5anos_1;custo_capital_10anos_1;custo_capital_20anos_1
"1/2005";16.32;12.7;12.68;12.73
"2/2005";16.91;12.81;12.69;12.73
"""

SPOT_RATE_CURVE_CSV = b"""\
,Date,1 month,2 months,3 months,6 months,1 year,3 years,5 years
0,2002-01-02,0.18998707830905914,0.18977642059326172,0.19011834263801575,0.19151726365089417,0.19860030710697174,,
1,2002-01-03,0.18938952684402466,0.18786495923995972,0.18764524161815643,0.18859028816223145,0.19462895393371582,,
"""

VOLATILITY_INDEX_CSV = b"""\
year,month,day,ivolbr
2011,8,1,21.28711
2011,8,2,23.56743
"""

DIVIDEND_YIELD_CSV = b"""\
ano,mes,dia,yield_week_pc
2001,2,2,.0072266
2001,2,9,.0072532
"""

LOAN_FEES_CSV = b"""\
ano,mes,dia,semana_aluguel_100
2013,1,4,.0210704
2013,1,11,.0166222
"""

SHORT_INTEREST_CSV = b"""\
date,average_short_interest
2012-11-07,32.501255248092974
2012-11-08,32.37419413069179
"""


def _mock_excel_response(sheets: dict) -> MagicMock:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    resp = MagicMock()
    resp.content = buf.getvalue()
    resp.raise_for_status = MagicMock()
    return resp


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_load_risk_factors_schema_and_values():
    with patch("nefin.core.requests.get", return_value=_mock_response(RISK_FACTORS_CSV)):
        df = nd.load_risk_factors()

    assert list(df.columns) == ["rm_minus_rf", "smb", "hml", "wml", "iml", "risk_free"]
    assert df.index.name == "date"
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index[0] == pd.Timestamp("2001-01-02")
    assert df.loc["2001-01-02", "smb"] == pytest.approx(0.115836998553672)


def test_load_cost_of_equity_single_sector():
    with patch("nefin.core.requests.get", return_value=_mock_response(COST_OF_EQUITY_CSV)) as get:
        df = nd.load_cost_of_equity(sector="consumer")

    assert "consumer.csv" in get.call_args[0][0]
    assert list(df.columns) == ["horizon_1y", "horizon_5y", "horizon_10y", "horizon_20y"]
    assert df.index.name == "date"
    assert df.index[0] == pd.Timestamp("2005-01-01")
    assert df.loc["2005-01-01", "horizon_1y"] == pytest.approx(16.32)


def test_load_cost_of_equity_all_sectors_returns_dict():
    with patch("nefin.core.requests.get", return_value=_mock_response(COST_OF_EQUITY_CSV)):
        result = nd.load_cost_of_equity()

    assert set(result.keys()) == set(COST_OF_EQUITY_SECTORS)
    for df in result.values():
        assert list(df.columns) == ["horizon_1y", "horizon_5y", "horizon_10y", "horizon_20y"]


def test_load_cost_of_equity_invalid_sector_raises():
    with pytest.raises(ValueError):
        nd.load_cost_of_equity(sector="not-a-sector")


def test_load_spot_rate_curve_schema():
    with patch("nefin.core.requests.get", return_value=_mock_response(SPOT_RATE_CURVE_CSV)):
        df = nd.load_spot_rate_curve()
    assert list(df.columns) == [
        "maturity_1m", "maturity_2m", "maturity_3m", "maturity_6m",
        "maturity_1y", "maturity_3y", "maturity_5y",
    ]
    assert df.index[0] == pd.Timestamp("2002-01-02")


def test_load_volatility_index_schema():
    with patch("nefin.core.requests.get", return_value=_mock_response(VOLATILITY_INDEX_CSV)):
        df = nd.load_volatility_index()
    assert list(df.columns) == ["ivol_br"]
    assert df.index[0] == pd.Timestamp("2011-08-01")
    assert df.loc["2011-08-01", "ivol_br"] == pytest.approx(21.28711)


def test_load_dividend_yield_schema():
    with patch("nefin.core.requests.get", return_value=_mock_response(DIVIDEND_YIELD_CSV)):
        df = nd.load_dividend_yield()
    assert list(df.columns) == ["dividend_yield"]
    assert df.index[0] == pd.Timestamp("2001-02-02")


def test_load_loan_fees_schema():
    with patch("nefin.core.requests.get", return_value=_mock_response(LOAN_FEES_CSV)):
        df = nd.load_loan_fees()
    assert list(df.columns) == ["loan_fee"]
    assert df.index[0] == pd.Timestamp("2013-01-04")


def test_load_short_interest_single_metric():
    with patch("nefin.core.requests.get", return_value=_mock_response(SHORT_INTEREST_CSV)):
        df = nd.load_short_interest(metric="short_interest")
    assert list(df.columns) == ["average_short_interest"]
    assert df.index[0] == pd.Timestamp("2012-11-07")


def test_load_short_interest_invalid_metric():
    with pytest.raises(ValueError):
        nd.load_short_interest(metric="bogus")


def test_load_risk_aversion_requires_excel_engine_or_parses():
    df_content = pd.DataFrame(
        {"year": [2011], "month": [9], "day": [2], "risk_aversion": [19.06]}
    )
    with patch(
        "nefin.core.requests.get",
        return_value=_mock_excel_response({"Sheet1": df_content}),
    ):
        df = nd.load_risk_aversion()
    assert list(df.columns) == ["risk_aversion"]
    assert df.index[0] == pd.Timestamp("2011-09-02")


def test_load_variance_premium_schema():
    df_content = pd.DataFrame(
        {"year": [2011], "month": [8], "day": [29], "premium": [-76.75]}
    )
    with patch(
        "nefin.core.requests.get",
        return_value=_mock_excel_response({"Sheet1": df_content}),
    ):
        df = nd.load_variance_premium()
    assert list(df.columns) == ["variance_premium"]


def test_load_portfolios_size():
    df_content = pd.DataFrame(
        {
            "year": [2001, 2001],
            "month": [1, 1],
            "day": [2, 3],
            "Size1": [0.0024, 0.0726],
            "Size2": [0.0314, 0.0724],
            "Size3": [0.0019, 0.0672],
        }
    )
    with patch(
        "nefin.core.requests.get",
        return_value=_mock_excel_response({"Equally Weighted Returns": df_content}),
    ):
        df = nd.load_portfolios(sort_by="size", n=3)
    assert list(df.columns) == ["size_1", "size_2", "size_3"]
    assert df.index[0] == pd.Timestamp("2001-01-02")


def test_load_portfolios_invalid_sort_by():
    with pytest.raises(ValueError):
        nd.load_portfolios(sort_by="not-a-sort")


def test_load_portfolios_invalid_n_for_sort_by():
    with pytest.raises(ValueError):
        nd.load_portfolios(sort_by="size", n=4)


def test_load_illiquidity_index_not_implemented():
    with pytest.raises(NotImplementedError, match="illiquidity-index"):
        nd.load_illiquidity_index()


def test_load_csv_escape_hatch():
    with patch("nefin.core.requests.get", return_value=_mock_response(RISK_FACTORS_CSV)):
        df = nd.load_csv("risk-factors", "nefin_factors", index_col=0)
    assert "Date" in df.columns


def test_get_url_escape_hatch():
    assert nd.get_url("cost-of-equity", "consumer", ext="csv") == (
        "https://nefin.com.br/nefindata/cost-of-equity/consumer.csv"
    )
