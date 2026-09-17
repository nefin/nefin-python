from unittest.mock import MagicMock, patch

import pytest

from nefin import core
from nefin.core import NefinDownloadError


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_get_url():
    assert (
        core.get_url("risk-factors", "nefin_factors")
        == "https://nefin.com.br/nefindata/risk-factors/nefin_factors.csv"
    )
    assert (
        core.get_url("cost-of-equity", "consumer", ext="xls")
        == "https://nefin.com.br/nefindata/cost-of-equity/consumer.xls"
    )


def test_load_csv_downloads_and_parses():
    csv_bytes = b"a,b\n1,2\n3,4\n"
    with patch("nefin.core.requests.get", return_value=_mock_response(csv_bytes)) as get:
        df = core.load_csv("risk-factors", "nefin_factors")
    get.assert_called_once()
    assert list(df.columns) == ["a", "b"]
    assert df.shape == (2, 2)


def test_load_csv_uses_cache_on_second_call():
    csv_bytes = b"a,b\n1,2\n"
    with patch("nefin.core.requests.get", return_value=_mock_response(csv_bytes)) as get:
        core.load_csv("risk-factors", "nefin_factors")
        core.load_csv("risk-factors", "nefin_factors")
    assert get.call_count == 1


def test_load_csv_bypasses_cache_when_disabled():
    csv_bytes = b"a,b\n1,2\n"
    with patch("nefin.core.requests.get", return_value=_mock_response(csv_bytes)) as get:
        core.load_csv("risk-factors", "nefin_factors", use_cache=False)
        core.load_csv("risk-factors", "nefin_factors", use_cache=False)
    assert get.call_count == 2


def test_load_csv_refetches_when_cache_expired():
    csv_bytes = b"a,b\n1,2\n"
    with patch("nefin.core.requests.get", return_value=_mock_response(csv_bytes)) as get:
        core.load_csv("risk-factors", "nefin_factors", ttl=0)
        core.load_csv("risk-factors", "nefin_factors", ttl=0)
    assert get.call_count == 2


def test_cache_read_oserror_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NEFIN_CACHE_DIR", str(tmp_path))
    cache_file = tmp_path / "risk-factors" / "nefin_factors.csv"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"a,b\n1,2\n")

    with patch("pathlib.Path.read_bytes", side_effect=OSError("permission denied")):
        with pytest.raises(NefinDownloadError, match="Could not read cached file"):
            core.load_csv("risk-factors", "nefin_factors")


def test_cache_write_oserror_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NEFIN_CACHE_DIR", str(tmp_path))
    csv_bytes = b"a,b\n1,2\n"

    with patch("nefin.core.requests.get", return_value=_mock_response(csv_bytes)):
        with patch("pathlib.Path.write_bytes", side_effect=OSError("disk full")):
            with pytest.raises(NefinDownloadError, match="could not write it to the cache"):
                core.load_csv("risk-factors", "nefin_factors")


def test_load_excel_missing_engine_raises_clear_error():
    xls_bytes = b"not a real xls file"
    with patch("nefin.core.requests.get", return_value=_mock_response(xls_bytes)):
        with patch("pandas.read_excel", side_effect=ImportError("no module named xlrd")):
            with pytest.raises(NefinDownloadError, match="no Excel engine is installed"):
                core.load_excel("portfolios", "3_portfolios_sorted_by_size")


def test_load_excel_unparseable_raises_clear_error():
    xls_bytes = b"not a real xls file"
    with patch("nefin.core.requests.get", return_value=_mock_response(xls_bytes)):
        with pytest.raises(NefinDownloadError, match="could not parse it as an Excel file"):
            core.load_excel("portfolios", "3_portfolios_sorted_by_size")
