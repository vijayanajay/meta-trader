import unittest
from unittest.mock import patch, call
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
            if not any(cache_path.iterdir()):
                cache_path.rmdir()

        self.service = MarketDataService(cache_dir=self.cache_dir)

    def tearDown(self):
        # Clean up cache directory after each test
        cache_path = Path(self.cache_dir)
        if cache_path.exists():
            for item in cache_path.iterdir():
                item.unlink()
            if not any(cache_path.iterdir()):
                cache_path.rmdir()

    @patch("praxis_engine.services.market_data_service.yf.download")
    def test_get_market_data_fetches_and_caches_data(self, mock_yf_download):
        """
        Test that data is fetched and cached when the cache is empty.
        """
        # Arrange
        tickers = ["^NSEI", "^INDIAVIX"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        mock_nse_df = pd.DataFrame({'Close': [18000, 18100]})
        mock_vix_df = pd.DataFrame({'Close': [12.5, 12.6]})
        mock_yf_download.side_effect = [mock_nse_df, mock_vix_df]

        # Act
        with patch("praxis_engine.services.market_data_service.pd.DataFrame.to_parquet") as mock_to_parquet:
            data_dict = self.service.get_market_data(tickers, start_date, end_date)

            # Assert
            self.assertIsInstance(data_dict, dict)
            self.assertIn("^NSEI", data_dict)
            self.assertIn("^INDIAVIX", data_dict)
            pd.testing.assert_frame_equal(data_dict["^NSEI"], mock_nse_df)
            pd.testing.assert_frame_equal(data_dict["^INDIAVIX"], mock_vix_df)

            # Check that yf.download was called for each ticker
            self.assertEqual(mock_yf_download.call_count, 2)
            mock_yf_download.assert_has_calls([
                call("^NSEI", start=start_date, end=end_date, progress=False, auto_adjust=False),
                call("^INDIAVIX", start=start_date, end=end_date, progress=False, auto_adjust=False)
            ], any_order=True)

            # Check that we are trying to save each df to cache
            self.assertEqual(mock_to_parquet.call_count, 2)

    @patch("praxis_engine.services.market_data_service.yf.download")
    @patch("praxis_engine.services.market_data_service.pd.read_parquet")
    def test_get_market_data_loads_from_cache(self, mock_read_parquet, mock_yf_download):
        """
        Test that data is loaded from the cache if it exists.
        """
        # Arrange
        tickers = ["^NSEI"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        mock_df = pd.DataFrame({"Close": [100, 101, 102]})
        mock_read_parquet.return_value = mock_df

        with patch("praxis_engine.services.market_data_service.Path.exists", return_value=True):
            # Act
            data_dict = self.service.get_market_data(tickers, start_date, end_date)

            # Assert
            self.assertIn("^NSEI", data_dict)
            pd.testing.assert_frame_equal(data_dict["^NSEI"], mock_df)
            mock_read_parquet.assert_called_once()
            mock_yf_download.assert_not_called()

    @patch("praxis_engine.services.market_data_service.yf.download")
    def test_get_market_data_handles_yfinance_error(self, mock_yf_download):
        """
        Test that the service handles errors from yfinance gracefully and returns an empty dict.
        """
        # Arrange
        mock_yf_download.side_effect = Exception("Test yfinance error")
        tickers = ["^FAIL"]
        start_date = "2023-01-01"
        end_date = "2023-01-31"

        # Act
        with patch("praxis_engine.services.market_data_service.log.error") as mock_log_error:
            data_dict = self.service.get_market_data(tickers, start_date, end_date)

            # Assert
            self.assertIsInstance(data_dict, dict)
            self.assertEqual(len(data_dict), 0)
            mock_log_error.assert_called_once_with(
                f"Error fetching market data for {tickers[0]}: Test yfinance error"
            )
