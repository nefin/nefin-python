import pytest


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path, monkeypatch):
    """Never touch the real ~/.cache/nefin during tests."""
    monkeypatch.setenv("NEFIN_CACHE_DIR", str(tmp_path / "cache"))
