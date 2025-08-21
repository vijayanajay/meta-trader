"""
Service for fetching and managing historical market data.
"""
import pandas as pd
from typing import Tuple

__all__ = ["DataService"]


class DataService:
    """
    Handles fetching, caching, and splitting of historical stock data.
    """
    def __init__(self, data_dir: str):
        self._data_dir = data_dir

    # impure
    def get_data(self, ticker: str, period: str, split_ratio: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Gets training and validation data for a given ticker.

        Returns:
            A tuple containing the training DataFrame and the validation DataFrame.
        """
        # This is a placeholder implementation.
        print(f"Fetching data for {ticker}...")
        return pd.DataFrame(), pd.DataFrame()
