# tests/test_data_service.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from services.data_service import DataService


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Creates a sample 10-year DataFrame for testing."""
    dates = pd.to_datetime(pd.date_range(start="2014-01-01", end="2023-12-31", freq="D"))
    return pd.DataFrame({"Close": range(len(dates))}, index=dates)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory for caching."""
    return tmp_path / "test_cache"


def test_get_data_downloads_and_caches_if_not_exists(
    temp_cache_dir: Path, sample_data: pd.DataFrame
) -> None:
    """Verify data is downloaded and cached when no cache file exists."""
    # Arrange
    service = DataService(data_dir=temp_cache_dir)
    ticker = "TEST.Ticker"
    cache_file = temp_cache_dir / "TEST.Ticker_2014-01-01_2023-12-31.parquet"

    with patch("yfinance.download", return_value=sample_data) as mock_download:
        # Act
        train_df, val_df = service.get_data(ticker)

        # Assert
        mock_download.assert_called_once_with(
            ticker, start="2014-01-01", end="2023-12-31", progress=False, auto_adjust=True
        )
        assert cache_file.exists()
        assert not train_df.empty
        assert not val_df.empty


def test_get_data_loads_from_cache_if_exists(
    temp_cache_dir: Path, sample_data: pd.DataFrame
) -> None:
    """Verify data is loaded from cache if a file already exists."""
    # Arrange
    service = DataService(data_dir=temp_cache_dir)
    ticker = "TEST.Ticker"
    cache_file = temp_cache_dir / "TEST.Ticker_2014-01-01_2023-12-31.parquet"
    sample_data.to_parquet(cache_file)

    with patch("yfinance.download") as mock_download:
        # Act
        train_df, val_df = service.get_data(ticker)

        # Assert
        mock_download.assert_not_called()
        assert not train_df.empty
        assert not val_df.empty
        # A simple check to ensure data is loaded
        assert len(train_df) + len(val_df) == len(sample_data)


def test_data_split_is_deterministic_and_correct(sample_data: pd.DataFrame) -> None:
    """Verify the 8-year train / 2-year validation split is correct."""
    # Arrange
    service = DataService(data_dir="dummy")  # Cache not used in this test logic

    with patch("yfinance.download", return_value=sample_data):
        # Act
        train_df, val_df = service.get_data("ANY_TICKER")

        # Assert
        expected_split_point = pd.to_datetime("2021-12-31")

        assert train_df.index.max().date() == expected_split_point.date()
        assert val_df.index.min().date() == (expected_split_point + pd.DateOffset(days=1)).date()
        assert val_df.index.max().date() == pd.to_datetime("2023-12-31").date()
        assert train_df.index.intersection(val_df.index).empty  # No overlap


def test_get_data_raises_ioerror_on_download_failure(temp_cache_dir: Path) -> None:
    """Verify an IOError is raised if yfinance fails."""
    # Arrange
    service = DataService(data_dir=temp_cache_dir)
    error_message = "Test download failure"

    with patch("yfinance.download", side_effect=Exception(error_message)):
        # Act & Assert
        with pytest.raises(IOError, match=f"Failed to download or save data for FAILED.TICKER: {error_message}"):
            service.get_data("FAILED.TICKER")


def test_get_data_raises_valueerror_on_empty_dataframe(temp_cache_dir: Path) -> None:
    """Verify a ValueError is raised if yfinance returns no data."""
    # Arrange
    service = DataService(data_dir=temp_cache_dir)
    empty_df = pd.DataFrame()

    with patch("yfinance.download", return_value=empty_df):
        # Act & Assert
        with pytest.raises(ValueError, match="No data found for ticker EMPTY.TICKER"):
            service.get_data("EMPTY.TICKER")
