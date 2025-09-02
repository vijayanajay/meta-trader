"""
Core Statistical Tests Library.

This module provides pure, well-tested functions for all required
statistical tests. These are the mathematical building blocks of the strategy
and must be provably correct.
"""
from typing import Optional

import numpy as np
import pandas as pd
import numba
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

@numba.jit(nopython=True)
def _calculate_hurst(time_series: np.ndarray, max_lag: int = 20) -> float:
    """
    Numba-jitted function to calculate the Hurst exponent.
    """
    lags = np.arange(2, max_lag)
    tau = [np.std(time_series[lag:] - time_series[:-lag]) for lag in lags]

    log_lags = np.log(lags)
    log_tau = np.log(np.array(tau))

    # manual linear regression
    n = len(log_lags)
    sum_x = np.sum(log_lags)
    sum_y = np.sum(log_tau)
    sum_xy = np.sum(log_lags * log_tau)
    sum_x2 = np.sum(log_lags**2)

    m = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)

    return m

def hurst_exponent(series: pd.Series, max_lag: int = 20) -> Optional[float]:
    """
    Calculates the Hurst Exponent of a time series.

    Args:
        series: The pandas Series to calculate the Hurst Exponent on.
        max_lag: The maximum lag to use for the calculation.

    Returns:
        The Hurst Exponent value, or None if calculation fails.
    """
    if len(series) < 100:
        return None

    try:
        return _calculate_hurst(series.to_numpy(), max_lag)
    except Exception:
        return None
