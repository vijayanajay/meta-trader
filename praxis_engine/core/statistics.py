"""
Core Statistical Tests Library.

This module provides pure, well-tested functions for all required
statistical tests. These are the mathematical building blocks of the strategy
and must be provably correct.
"""
from typing import Optional

import numpy as np
import pandas as pd
from hurst import compute_Hc
from statsmodels.tsa.stattools import adfuller


def adf_test(series: pd.Series) -> Optional[float]:
    """
    Performs the Augmented Dickey-Fuller test.

    Args:
        series: The pandas Series to test.

    Returns:
        The p-value of the test, or None if the test fails.
    """
    if series.empty:
        return None
    try:
        result = adfuller(series)
        return float(result[1])
    except Exception:
        return None


def hurst_exponent(series: pd.Series) -> Optional[float]:
    """
    Calculates the Hurst Exponent of a time series using the `hurst` library.

    Args:
        series: The pandas Series to calculate the Hurst Exponent on.

    Returns:
        The Hurst Exponent value, or None if calculation fails.
    """
    if len(series) < 100:
        return None

    try:
        H, _, _ = compute_Hc(series, kind='random_walk', simplified=True)
        return float(H)
    except Exception:
        return None
