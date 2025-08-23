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
        """
        cache_file = self.cache_dir / f"{stock}_{start_date}_{end_date}.parquet"
        # If cache exists and is valid, use it.
        if cache_file.exists():
            df = pd.read_parquet(cache_file)
            if not (sector_ticker and "sector_vol" not in df.columns):
                log.info(f"Loading {stock} data from cache.")
                return df
            log.warning(f"Cache for {stock} is stale (missing sector_vol). Re-fetching.")

        # Otherwise, download fresh data.
        try:
            log.info(f"Fetching fresh data for {stock}.")
            df = yf.download(stock, start=start_date, end=end_date, progress=False)
            if df.empty:
                log.warning(f"No data returned from yfinance for {stock}.")
                return None

            if sector_ticker:
                df = self._add_sector_vol(df, sector_ticker, start_date, end_date)

            if df is not None:
                log.info(f"Saving {stock} data to cache.")
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
