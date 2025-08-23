import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from praxis_engine.services.data_service import DataService

def test_get_data_from_cache(tmp_path: Path) -> None:
    """
    Tests that data is loaded from the cache if it exists.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    stock = "TEST"
    start_date = "2022-01-01"
    end_date = "2022-01-31"
    cache_file = cache_dir / f"{stock}_{start_date}_{end_date}.parquet"

    # Create a dummy cache file
    dummy_df = pd.DataFrame({"Close": [1, 2, 3]})
    dummy_df.to_parquet(cache_file)

    service = DataService(cache_dir=str(cache_dir))
    df = service.get_data(stock, start_date, end_date)

    assert df is not None
    pd.testing.assert_frame_equal(df, dummy_df)

@patch("yfinance.download")
def test_get_data_from_api(mock_yf_download: MagicMock, tmp_path: Path) -> None:
    """
    Tests that data is fetched from the yfinance API if not in cache.
    """
    cache_dir = tmp_path / "cache"
    stock = "TEST"
    start_date = "2022-01-01"
    end_date = "2022-01-31"

    # Mock yfinance download
    mock_df = pd.DataFrame({"Close": [10, 20, 30]})
    mock_yf_download.return_value = mock_df

    service = DataService(cache_dir=str(cache_dir))
    df = service.get_data(stock, start_date, end_date)

    assert df is not None
    pd.testing.assert_frame_equal(df, mock_df)

    # Verify it was cached
    cache_file = cache_dir / f"{stock}_{start_date}_{end_date}.parquet"
    assert cache_file.exists()

@patch("yfinance.download")
def test_sector_volatility_calculation(mock_yf_download: MagicMock, tmp_path: Path) -> None:
    """
    Tests that sector volatility is calculated and added to the DataFrame.
    """
    cache_dir = tmp_path / "cache"
    stock = "RELIANCE.NS"
    sector_ticker = "^NSEI"
    start_date = "2022-01-01"
    end_date = "2022-01-31"

    # Create a date range for the mock data
    dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))

    stock_df = pd.DataFrame({"Close": [100 + i for i in range(len(dates))]}, index=dates)
    sector_df = pd.DataFrame({"Close": [1000 + i for i in range(len(dates))]}, index=dates)

    # The first call is for the stock, the second for the sector
    mock_yf_download.side_effect = [stock_df, sector_df]

    service = DataService(cache_dir=str(cache_dir))
    df = service.get_data(stock, start_date, end_date, sector_ticker=sector_ticker)

    assert df is not None
    assert "sector_vol" in df.columns
    assert not df["sector_vol"].dropna().empty

@patch("yfinance.download")
def test_get_data_api_failure(mock_yf_download: MagicMock, tmp_path: Path) -> None:
    """
    Tests that the service handles API failures gracefully.
    """
    cache_dir = tmp_path / "cache"
    stock = "FAIL"
    start_date = "2022-01-01"
    end_date = "2022-01-31"

    # Simulate an API failure
    mock_yf_download.side_effect = Exception("API is down")

    service = DataService(cache_dir=str(cache_dir))
    df = service.get_data(stock, start_date, end_date)

    assert df is None
