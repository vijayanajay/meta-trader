from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from self_improving_quant.services.data_service import (
    CACHE_EXPIRY_HOURS,
    CACHE_FILE,
    fetch_and_split_data,
)

TICKER = "RELIANCE.NS"
MOCK_DATA_YEARS = 10


def create_mock_df() -> pd.DataFrame:
    """Creates a mock DataFrame spanning the required number of years."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=MOCK_DATA_YEARS * 365)
    dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq="D"))
    return pd.DataFrame(index=dates, data={"Close": range(len(dates))})


@pytest.fixture
def mock_yf_download() -> Iterator[MagicMock]:
    """Fixture to mock yfinance.download."""
    with patch("self_improving_quant.services.data_service.yf.download") as mock:
        mock.return_value = create_mock_df()
        yield mock


@pytest.fixture
def mock_pd_read_parquet() -> Iterator[MagicMock]:
    """Fixture to mock pandas.read_parquet."""
    with patch("self_improving_quant.services.data_service.pd.read_parquet") as mock:
        mock.return_value = create_mock_df()
        yield mock


@pytest.fixture
def mock_cache_file() -> Iterator[MagicMock]:
    """Fixture to mock the CACHE_FILE Path object."""
    with patch("self_improving_quant.services.data_service.CACHE_FILE") as mock:
        yield mock


@patch("pandas.DataFrame.to_parquet")
def test_fetch_no_cache(
    mock_to_parquet: MagicMock, mock_yf_download: MagicMock, mock_cache_file: MagicMock
) -> None:
    """Test fetching data when no cache file exists."""
    mock_cache_file.exists.return_value = False

    train_df, val_df = fetch_and_split_data(TICKER)

    mock_yf_download.assert_called_once()
    mock_to_parquet.assert_called_once()
    assert not train_df.empty
    assert not val_df.empty


def test_fetch_with_fresh_cache(
    mock_pd_read_parquet: MagicMock, mock_yf_download: MagicMock, mock_cache_file: MagicMock
) -> None:
    """Test fetching data when a fresh cache file exists."""
    mock_cache_file.exists.return_value = True

    fresh_mod_time = datetime.now().timestamp()
    mock_cache_file.stat.return_value.st_mtime = fresh_mod_time

    train_df, val_df = fetch_and_split_data(TICKER)

    mock_pd_read_parquet.assert_called_once()
    mock_yf_download.assert_not_called()
    assert not train_df.empty
    assert not val_df.empty


@patch("pandas.DataFrame.to_parquet")
def test_fetch_with_stale_cache(
    mock_to_parquet: MagicMock, mock_yf_download: MagicMock, mock_cache_file: MagicMock
) -> None:
    """Test fetching data when a stale cache file exists."""
    mock_cache_file.exists.return_value = True

    stale_mod_time = (datetime.now() - timedelta(hours=CACHE_EXPIRY_HOURS + 1)).timestamp()
    mock_cache_file.stat.return_value.st_mtime = stale_mod_time

    train_df, val_df = fetch_and_split_data(TICKER)

    mock_yf_download.assert_called_once()
    mock_to_parquet.assert_called_once()
    assert not train_df.empty
    assert not val_df.empty
