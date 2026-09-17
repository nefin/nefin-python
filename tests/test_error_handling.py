from unittest.mock import MagicMock, patch

import pytest
import requests

import nefin as nd
from nefin.core import NefinDownloadError


def _mock_http_error(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    error = requests.exceptions.HTTPError(response=resp)
    resp.raise_for_status.side_effect = error
    return resp


def test_http_404_raises_clear_error():
    with patch("nefin.core.requests.get", return_value=_mock_http_error(404)):
        with pytest.raises(NefinDownloadError, match="404"):
            nd.load_risk_factors(use_cache=False)


def test_connection_error_raises_clear_error():
    with patch(
        "nefin.core.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        with pytest.raises(NefinDownloadError, match="download"):
            nd.load_risk_factors(use_cache=False)


def test_timeout_raises_clear_error():
    with patch(
        "nefin.core.requests.get",
        side_effect=requests.exceptions.Timeout("boom"),
    ):
        with pytest.raises(NefinDownloadError, match="Timed out"):
            nd.load_risk_factors(use_cache=False)


def test_unparseable_content_raises_clear_error():
    resp = MagicMock()
    resp.content = b""  # empty response body -> pandas EmptyDataError
    resp.raise_for_status = MagicMock()
    with patch("nefin.core.requests.get", return_value=resp):
        with pytest.raises(NefinDownloadError):
            nd.load_risk_factors(use_cache=False)


def test_schema_drift_inside_a_loader_wraps_as_clear_error():
    # Valid CSV that parses fine but is missing the columns load_risk_factors
    # expects — simulates NEFIN silently renaming/dropping a column, which
    # should surface as NefinDownloadError, not a raw pandas KeyError.
    resp = MagicMock()
    resp.content = b"Unexpected,Columns\n1,2\n"
    resp.raise_for_status = MagicMock()
    with patch("nefin.core.requests.get", return_value=resp):
        with pytest.raises(NefinDownloadError, match="load_risk_factors"):
            nd.load_risk_factors(use_cache=False)


def test_portfolio_invalid_sort_by_is_plain_value_error():
    with pytest.raises(ValueError, match="sort_by"):
        nd.load_portfolios(sort_by="not-a-sort", use_cache=False)


def test_portfolio_invalid_n_is_plain_value_error():
    with pytest.raises(ValueError, match="not available"):
        nd.load_portfolios(sort_by="size", n=4, use_cache=False)


def test_short_interest_invalid_metric_is_plain_value_error():
    with pytest.raises(ValueError, match="Unknown metric"):
        nd.load_short_interest(metric="bogus", use_cache=False)


def test_cost_of_equity_invalid_sector_is_plain_value_error():
    with pytest.raises(ValueError, match="sector"):
        nd.load_cost_of_equity(sector="bogus", use_cache=False)


def test_illiquidity_index_not_implemented():
    with pytest.raises(NotImplementedError, match="not published"):
        nd.load_illiquidity_index()
