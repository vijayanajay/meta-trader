"""
This service is responsible for fetching and caching market-wide data, such as
indices and volatility measures.
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import List, Dict

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
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetches data for a given list of market tickers, with per-ticker caching.

        Args:
            tickers: A list of market tickers (e.g., ['^NSEI', '^INDIAVIX']).
            start: The start date for the data.
            end: The end date for the data.

        Returns:
            A dictionary where keys are tickers and values are their OHLCV DataFrames.
            Returns an empty dictionary if all tickers fail.
        """
        all_data: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            safe_ticker = ticker.replace("^", "").replace("/", "_")
            cache_file = self.cache_dir / f"{safe_ticker}_{start}_{end}.parquet"

            if cache_file.exists():
                log.info(f"Loading market data for {ticker} from cache: {cache_file}")
                df = pd.read_parquet(cache_file)
            else:
                try:
                    log.info(f"Fetching fresh market data for {ticker}.")
                    df = yf.download(
                        ticker, start=start, end=end, progress=False, auto_adjust=False
                    )

                    if df.empty:
                        log.warning(f"No market data returned from yfinance for {ticker}.")
                        continue

                    log.info(f"Saving market data for {ticker} to cache: {cache_file}")
                    df.to_parquet(cache_file)

                except Exception as e:
                    log.error(f"Error fetching market data for {ticker}: {e}")
                    continue

            all_data[ticker] = df

        return all_data
