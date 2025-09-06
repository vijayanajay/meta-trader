import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path

from praxis_engine.services.market_data_service import MarketDataService


class TestMarketDataService(unittest.TestCase):
    def setUp(self):
        self.cache_dir = "test_cache/market"
        # Clean up cache directory before each test to ensure a clean state
        cache_path = Path(self.cache_dir)
        if cache_path.exists():
            for item in cache_path.iterdir():
                item.unlink()
            cache_path.rmdir()

        self.service = MarketDataService(cache_dir=self.cache_dir)

    def tearDown(self):
        # Clean up cache directory after each test
        cache_path = Path(self.cache_dir)
        if cache_path.exists():
            for item in cache_path.iterdir():
                item.unlink()
            cache_path.rmdir()

    @patch("praxis_engine.services.market_data_service.yf.download")
    def test_get_market_data_fetches_and_caches_data(self, mock_yf_download):
        """
        Test that data is fetched and cached when the cache is empty.
        This test also verifies the multi-ticker response handling.
        """
        # Arrange
        tickers = ["^NSEI", "^INDIAVIX"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        # Create a realistic multi-index DataFrame, as yfinance does for multiple tickers
        mock_data = {
            ('Close', '^NSEI'): [18000, 18100],
            ('Close', '^INDIAVIX'): [12.5, 12.6]
        }
        mock_df = pd.DataFrame(mock_data)
        mock_df.columns = pd.MultiIndex.from_tuples(mock_df.columns)
        mock_yf_download.return_value = mock_df

        # Act
        with patch("praxis_engine.services.market_data_service.pd.DataFrame.to_parquet") as mock_to_parquet:
            df = self.service.get_market_data(tickers, start_date, end_date)

            # Assert
            self.assertIsNotNone(df)
            self.assertListEqual(list(df.columns), ['NSEI_close', 'INDIAVIX_close'])
            mock_yf_download.assert_called_once_with(
                tickers, start=start_date, end=end_date, progress=False, auto_adjust=False
            )
            # Check that we are trying to save the processed data to cache
            mock_to_parquet.assert_called_once()
            # Check that the service constructor created the cache directory
            self.assertTrue(Path(self.cache_dir).exists())

    @patch("praxis_engine.services.market_data_service.yf.download")
    @patch("praxis_engine.services.market_data_service.pd.read_parquet")
    @patch("praxis_engine.services.market_data_service.Path.exists")
    def test_get_market_data_loads_from_cache(
        self, mock_path_exists, mock_read_parquet, mock_yf_download
    ):
        """
        Test that data is loaded from the cache if it exists.
        """
        # Arrange
        mock_path_exists.return_value = True
        mock_df = pd.DataFrame({"NSEI_close": [100, 101, 102]})
        mock_read_parquet.return_value = mock_df
        tickers = ["^NSEI"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        # Act
        df = self.service.get_market_data(tickers, start_date, end_date)

        # Assert
        self.assertIsNotNone(df)
        mock_read_parquet.assert_called_once()
        mock_yf_download.assert_not_called()

    @patch("praxis_engine.services.market_data_service.yf.download")
    def test_get_market_data_handles_yfinance_error(self, mock_yf_download):
        """
        Test that the service handles errors from yfinance gracefully.
        """
        # Arrange
        mock_yf_download.side_effect = Exception("Test yfinance error")
        tickers = ["^FAIL"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        # Act
        with patch("praxis_engine.services.market_data_service.log.error") as mock_log_error:
            df = self.service.get_market_data(tickers, start_date, end_date)

            # Assert
            self.assertIsNone(df)
            mock_log_error.assert_called_once_with(
                f"Error fetching market data for {tickers}: Test yfinance error"
            )
