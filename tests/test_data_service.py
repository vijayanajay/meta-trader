"""
Unit tests for the DataService.
"""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from praxis_engine.services.data_service import DataService

@pytest.fixture
def data_service(tmp_path) -> DataService:
    """Fixture for DataService."""
    return DataService(cache_dir=str(tmp_path))

@patch('yfinance.download')
def test_get_data_fresh_download(mock_download: MagicMock, data_service: DataService) -> None:
    """Test fetching data for the first time."""
    mock_df = pd.DataFrame({'Close': [100, 101]})
    mock_download.return_value = mock_df

    df = data_service.get_data("TEST.NS", "2023-01-01", "2023-01-02", "SECTOR")

    assert df is not None
    assert not df.empty
    mock_download.assert_called()

@patch('yfinance.download')
def test_get_data_caching(mock_download: MagicMock, data_service: DataService) -> None:
    """Test that data is cached and retrieved on second call."""
    mock_df = pd.DataFrame({'Close': [100, 101]})
    mock_download.return_value = mock_df

    # First call - should download and cache
    data_service.get_data("TEST.NS", "2023-01-01", "2023-01-02", "SECTOR")

    # Second call - should use cache
    data_service.get_data("TEST.NS", "2023-01-01", "2023-01-02", "SECTOR")

    assert mock_download.call_count == 2 # Once for stock, once for sector

@patch('yfinance.download')
def test_get_data_api_error(mock_download: MagicMock, data_service: DataService) -> None:
    """Test handling of API errors."""
    mock_download.side_effect = Exception("API Error")
    df = data_service.get_data("FAIL.NS", "2023-01-01", "2023-01-02")
    assert df is None

@patch('yfinance.download')
def test_add_sector_vol(mock_download: MagicMock, data_service: DataService) -> None:
    """Test that sector volatility is added correctly."""
    stock_df = pd.DataFrame({'Close': [100, 101, 102, 103, 104]})
    sector_df = pd.DataFrame({'Close': [50, 51, 50, 52, 53]})

    # Simulate yf.download being called twice: first for stock, then for sector
    mock_download.side_effect = [stock_df, sector_df]

    df = data_service.get_data("TEST.NS", "2023-01-01", "2023-01-05", "^NSEI")

    assert df is not None
    assert 'sector_vol' in df.columns
