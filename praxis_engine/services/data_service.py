"""
This service is responsible for fetching and caching financial data.
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import Optional

from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

class DataService:
    """
    A service for fetching and caching financial data.
    """

    def __init__(self, cache_dir: str = "data_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # impure
    def get_data(
        self,
        stock: str,
        start_date: str,
        end_date: str,
        sector_ticker: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetches data for a given stock, with caching.

        Args:
            stock: The stock ticker.
            start_date: The start date in YYYY-MM-DD format.
            end_date: The end date in YYYY-MM-DD format.
            sector_ticker: The ticker for the sector index.

        Returns:
            A pandas DataFrame with the stock data, or None if data cannot be fetched.
        """
        cache_file = self.cache_dir / f"{stock}_{start_date}_{end_date}.parquet"

        if cache_file.exists():
            df = pd.read_parquet(cache_file)
            # Ensure the sector vol is calculated if it was missed before
            if sector_ticker and "sector_vol" not in df.columns:
                return self._add_sector_vol(df, sector_ticker, start_date, end_date)
            return df


        try:
            df = yf.download(stock, start=start_date, end=end_date, progress=False)
            if df.empty:
                return None

            if sector_ticker:
                df = self._add_sector_vol(df, sector_ticker, start_date, end_date)


            df.to_parquet(cache_file)
            return df
        except Exception as e:
            log.error(f"Error fetching data for {stock}: {e}")
            return None

    # impure
    def _add_sector_vol(self, df: pd.DataFrame, sector_ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Adds sector volatility to the dataframe.
        """
        sector_df = yf.download(
            sector_ticker, start=start_date, end=end_date, progress=False
        )
        if not sector_df.empty:
            sector_vol = (
                sector_df["Close"].pct_change().rolling(window=20).std()
                * (252**0.5)
            )
            df["sector_vol"] = sector_vol
        return df
