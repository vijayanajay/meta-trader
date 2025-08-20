from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

__all__ = ["fetch_and_split_data"]

logger = logging.getLogger(__name__)


# impure: Performs network I/O to yfinance
def fetch_and_split_data(
    ticker: str,
    train_years: int = 8,
    validation_years: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetches historical stock data and splits it into training and validation sets.

    Args:
        ticker: The stock ticker symbol to fetch.
        train_years: The number of years for the training set.
        validation_years: The number of years for the validation set.

    Returns:
        A tuple containing the training DataFrame and the validation DataFrame.
    """
    total_years = train_years + validation_years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(total_years * 365.25))

    logger.info(f"Fetching {total_years} years of data for {ticker}...")
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            raise ValueError(f"No data found for ticker {ticker}.")
    except Exception as e:
        logger.error(f"Failed to download data for {ticker}: {e}")
        raise

    # Split data
    split_date = end_date - timedelta(days=int(validation_years * 365.25))
    train_data = data[data.index < split_date]
    validation_data = data[data.index >= split_date]

    logger.info(f"Data split. Training: {len(train_data)} rows, Validation: {len(validation_data)} rows.")
    return train_data, validation_data
