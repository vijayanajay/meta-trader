"""
Core Technical Indicators Library.

This module provides pure, well-tested functions for all required
technical indicators. These are the mathematical building blocks of the strategy
and must be provably correct.
"""
from typing import Optional

import pandas as pd


def bbands(
    series: pd.Series, length: int = 20, std: float = 2.0
) -> Optional[pd.DataFrame]:
    """
    Calculates Bollinger Bands.

    Args:
        series: The pandas Series to calculate the Bollinger Bands on.
        length: The moving average period.
        std: The standard deviation multiplier.

    Returns:
        A pandas DataFrame with Bollinger Bands columns or None if calculation fails.
    """
    if series.empty or len(series) < length:
        return None

    middle_band = series.rolling(window=length).mean()
    std_dev = series.rolling(window=length).std()

    upper_band = middle_band + (std_dev * std)
    lower_band = middle_band - (std_dev * std)

    df = pd.DataFrame({
        f"BBL_{length}_{std}": lower_band,
        f"BBM_{length}_{std}": middle_band,
        f"BBU_{length}_{std}": upper_band,
    })
    return df


def rsi(series: pd.Series, length: int = 14) -> Optional[pd.Series]:
    """
    Calculates the Relative Strength Index (RSI).

    Args:
        series: The pandas Series to calculate the RSI on.
        length: The RSI period.

    Returns:
        A pandas Series with RSI values or None if calculation fails.
    """
    if series.empty or len(series) < length:
        return None

    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()

    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi_series.name = f"RSI_{length}"

    return rsi_series
