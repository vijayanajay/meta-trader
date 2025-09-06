"""
This service is responsible for fetching and caching market-wide data, such as
indices and volatility measures.
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import List, Optional

from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class MarketDataService:
    """
    A service for fetching and caching market-wide data.
    """

    def __init__(self, cache_dir: str = "data_cache/market") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # impure
    def get_market_data(
        self, tickers: List[str], start: str, end: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetches data for a given list of market tickers, with caching.

        Args:
            tickers: A list of market tickers (e.g., ['^NSEI', '^INDIAVIX']).
            start: The start date for the data.
            end: The end date for the data.
        """
        # Sanitize tickers for filename
        safe_tickers = "_".join(t.replace("^", "") for t in tickers)
        cache_file = self.cache_dir / f"{safe_tickers}_{start}_{end}.parquet"

        if cache_file.exists():
            log.info(f"Loading market data for {tickers} from cache.")
            return pd.read_parquet(cache_file)

        try:
            log.info(f"Fetching fresh market data for {tickers}.")
            df = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=False)

            if df.empty:
                log.warning(f"No market data returned from yfinance for {tickers}.")
                return None

            # For single ticker, yfinance returns a simple column structure.
            # For multiple tickers, it returns a MultiIndex. We want to handle both.
            if isinstance(df.columns, pd.MultiIndex):
                # We only care about the 'Close' prices for market data.
                df = df['Close']
                df.columns = [f"{t.replace('^', '')}_close" for t in tickers]
            else:
                # If single ticker, rename columns for consistency
                df.rename(columns={'Close': f"{tickers[0].replace('^', '')}_close"}, inplace=True)


            log.info(f"Saving market data for {tickers} to cache.")
            df.to_parquet(cache_file)
            return df
        except Exception as e:
            log.error(f"Error fetching market data for {tickers}: {e}")
            return None
