"""
Indicator precomputation helper.

This module centralizes the precomputation of recurring indicators (BBands, RSI, ATR,
weekly/monthly BBands, rolling Hurst and ADF columns) and merges them into the
original dataframe. It replaces duplicated logic previously spread in the
Orchestrator.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd

from praxis_engine.core.indicators import bbands, rsi, atr
from praxis_engine.core.statistics import hurst_exponent, adf_test
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


def _safe_reindex_and_ffill(series: pd.DataFrame | pd.Series, target_index: pd.Index) -> Optional[pd.DataFrame]:
    try:
        return series.reindex(target_index, method="ffill")
    except (KeyError, TypeError, ValueError) as e:
        log.warning(f"Failed to reindex series for weekly/monthly indicators: {e}")
        return None


def rolling_apply_series(series: pd.Series, window: int, func) -> pd.Series:
    """Wrapper for rolling.apply that passes a Series to `func` and returns a Series.

    This helper ensures consistent handling of short windows and exceptions.
    """
    if window <= 0:
        raise ValueError("window must be positive")

    def _wrapped(arr):
        try:
            s = pd.Series(arr)
            if s.dropna().size < window:
                return float("nan")
            return float(func(s))
        except (ValueError, TypeError) as e:
            # Return nan and let caller handle logging if necessary
            return float("nan")

    return series.rolling(window=window).apply(_wrapped, raw=True)


def precompute_indicators(full_df: pd.DataFrame, config) -> pd.DataFrame:
    """Precompute and merge indicator columns into a copy of `full_df`.

    Args:
        full_df: Original OHLCV dataframe indexed by date.
        config: Full Config object (Pydantic) containing strategy params.

    Returns:
        DataFrame: A new dataframe with indicator columns merged. On failure,
        returns the original df (a shallow copy) with best-effort additions.
    """
    df = full_df.copy()
    params = config.strategy_params

    # Daily BB, RSI, ATR
    try:
        bb_daily = bbands(df["Close"], length=params.bb_length, std=params.bb_std)
        if bb_daily is not None:
            df = pd.concat([df, bb_daily], axis=1)
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"bbands daily precompute failed: {e}")

    try:
        rsi_series = rsi(df["Close"], length=params.rsi_length)
        if rsi_series is not None:
            df = pd.concat([df, rsi_series], axis=1)
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"rsi precompute failed: {e}")

    try:
        atr_series = atr(df["High"], df["Low"], df["Close"], length=config.exit_logic.atr_period)
        if atr_series is not None:
            df = pd.concat([df, atr_series], axis=1)
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"atr precompute failed: {e}")

    # Weekly and monthly BBands (resample then forward-fill to daily index)
    try:
        df_weekly = df.resample("W-MON").last()
        if not df_weekly.empty:
            bb_weekly = bbands(df_weekly["Close"], length=10, std=2.5)
            if bb_weekly is not None:
                bb_weekly = _safe_reindex_and_ffill(bb_weekly, df.index)
                if bb_weekly is not None:
                    df = pd.concat([df, bb_weekly], axis=1)
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"weekly bbands precompute failed: {e}")

    try:
        df_monthly = df.resample("MS").last()
        if not df_monthly.empty:
            bb_monthly = bbands(df_monthly["Close"], length=6, std=3.0)
            if bb_monthly is not None:
                bb_monthly = _safe_reindex_and_ffill(bb_monthly, df.index)
                if bb_monthly is not None:
                    df = pd.concat([df, bb_monthly], axis=1)
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"monthly bbands precompute failed: {e}")

    # Rolling statistical precomputations for Hurst and ADF
    hurst_col = f"HURST_{params.hurst_length}"
    adf_col = f"ADF_{params.hurst_length}"

    try:
        df[hurst_col] = rolling_apply_series(df["Close"], params.hurst_length, lambda s: hurst_exponent(s))
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"hurst precompute failed: {e}")
        df[hurst_col] = float("nan")

    try:
        returns = df["Close"].pct_change()
        df[adf_col] = rolling_apply_series(returns, params.hurst_length, lambda s: adf_test(s.dropna()))
    except (KeyError, ValueError, TypeError) as e:
        log.warning(f"adf precompute failed: {e}")
        df[adf_col] = float("nan")

    return df
