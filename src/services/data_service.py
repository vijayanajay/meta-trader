# src/services/data_service.py
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import yfinance as yf
from pandas import DataFrame

__all__: list[str] = ["DataService"]


class DataService:
    """A service for fetching, caching, and splitting financial data."""

    def __init__(self, data_dir: Path | str) -> None:
        """
        Initializes the DataService.

        Args:
            data_dir: The directory to use for caching data files.
        """
        self._cache_dir = Path(data_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # impure
    def get_data(
        self, ticker: str, start_date: str = "2014-01-01", end_date: str = "2023-12-31"
    ) -> Tuple[DataFrame, DataFrame]:
        """
        Fetches and splits data for a given ticker.

        It caches data in Parquet format to avoid repeated downloads.
        The data is split into an 8-year training set and a 2-year validation set.

        Args:
            ticker: The stock ticker symbol.
            start_date: The start date for data download (YYYY-MM-DD).
            end_date: The end date for data download (YYYY-MM-DD).

        Returns:
            A tuple containing the training DataFrame and the validation DataFrame.
        """
        cache_file = self._cache_dir / f"{ticker}_{start_date}_{end_date}.parquet"

        if cache_file.exists():
            data = pd.read_parquet(cache_file)
        else:
            try:
                # Disable progress bar to keep logs clean
                data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
                if data.empty:
                    raise ValueError(f"No data found for ticker {ticker} in the given date range.")
                data.to_parquet(cache_file)
            except ValueError as e:
                raise e # Re-raise the specific validation error
            except Exception as e:
                # Catching generic Exception is broad, but yfinance can raise various errors
                raise IOError(f"Failed to download or save data for {ticker}: {e}") from e

        # yfinance can return a MultiIndex even for a single ticker.
        # We flatten the columns to a simple index (e.g., ('Open', 'TICK') -> 'Open').
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Normalize column names to TitleCase as expected by backtesting.py
        data.columns = [str(col).title() for col in data.columns]

        # Deterministic split: 2 years for validation, the rest for training
        end_of_data = data.index.max()
        split_point = end_of_data - pd.DateOffset(years=2)

        train_data = data.loc[data.index <= split_point]
        validation_data = data.loc[data.index > split_point]

        if train_data.empty or validation_data.empty:
            raise ValueError("Data split resulted in empty training or validation set.")

        return train_data, validation_data
