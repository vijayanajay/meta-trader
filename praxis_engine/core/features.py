from typing import Dict

import pandas as pd


def calculate_market_features(
    market_data: Dict[str, pd.DataFrame], nifty_ticker: str, vix_ticker: str
) -> pd.DataFrame:
    """
    Calculates market-wide features for the regime model.

    This function is pure and relies on the caller to provide the correct data.

    Args:
        market_data: A dictionary where keys are tickers and values are OHLCV DataFrames.
                     Expected to contain data for Nifty 50 and India VIX.
        nifty_ticker: The ticker symbol for the Nifty 50 index.
        vix_ticker: The ticker symbol for the India VIX index.

    Returns:
        A DataFrame with a DatetimeIndex and columns for each calculated feature.
    """
    if nifty_ticker not in market_data:
        raise ValueError(f"Nifty ticker '{nifty_ticker}' not found in market_data.")
    if vix_ticker not in market_data:
        raise ValueError(f"VIX ticker '{vix_ticker}' not found in market_data.")

    nifty_df = market_data[nifty_ticker]
    vix_df = market_data[vix_ticker]

    # Feature 1: Nifty vs. 200-day Moving Average
    nifty_close = nifty_df["Close"]
    nifty_sma_200 = nifty_close.rolling(window=200, min_periods=200).mean()
    nifty_vs_200ma = nifty_close / nifty_sma_200
    nifty_vs_200ma.name = "nifty_vs_200ma"

    # Feature 2: VIX Level
    vix_level = vix_df["Close"].copy() # Use copy to avoid SettingWithCopyWarning
    vix_level.name = "vix_level"

    # Feature 3: VIX 10-day Rate of Change
    vix_roc_10d = vix_level.pct_change(periods=10)
    vix_roc_10d.name = "vix_roc_10d"

    # Combine all features into a single DataFrame
    features_df = pd.concat([nifty_vs_200ma, vix_level, vix_roc_10d], axis=1)

    return features_df
