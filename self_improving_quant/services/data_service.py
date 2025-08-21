from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from self_improving_quant.utils.retry import retry_on_failure

__all__ = ["fetch_and_split_data"]

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "stock_data.parquet"
CACHE_EXPIRY_HOURS = 24


# impure: Performs file I/O and network I/O to yfinance
def fetch_and_split_data(
    ticker: str,
    train_years: int = 8,
    validation_years: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetches historical stock data, caches it, and splits it into training and validation sets.

    Args:
        ticker: The stock ticker symbol to fetch.
        train_years: The number of years for the training set.
        validation_years: The number of years for the validation set.

    Returns:
        A tuple containing the training DataFrame and the validation DataFrame.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    data: pd.DataFrame | None = None

    if CACHE_FILE.exists():
        expiry_time = datetime.now() - timedelta(hours=CACHE_EXPIRY_HOURS)
        file_mod_time = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        if file_mod_time > expiry_time:
            logger.info(f"Loading data from fresh cache file: {CACHE_FILE}")
            data = pd.read_parquet(CACHE_FILE)
        else:
            logger.info("Cache file is stale. Fetching new data.")

    if data is None:
        total_years = train_years + validation_years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(total_years * 365.25))

        logger.info(f"Fetching {total_years} years of data for {ticker}...")
        data = _download_with_retry(ticker, start_date, end_date)
        data.to_parquet(CACHE_FILE)
        logger.info(f"Saved new data to cache: {CACHE_FILE}")

    # Split data
    split_date = data.index.max() - timedelta(days=int(validation_years * 365.25))
    train_data = data[data.index < split_date]
    validation_data = data[data.index >= split_date]

    logger.info(f"Data split. Training: {len(train_data)} rows, Validation: {len(validation_data)} rows.")
    return train_data, validation_data


# impure: Performs network I/O to yfinance
@retry_on_failure(retries=3, delay=5, backoff=2, exceptions=(Exception,))
def _download_with_retry(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """A wrapper for yf.download that includes retry logic."""
    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        # yfinance doesn't always raise an error for invalid tickers,
        # so we must check for an empty DataFrame.
        raise ValueError(f"No data found for ticker '{ticker}'. It may be an invalid ticker.")
    return data
