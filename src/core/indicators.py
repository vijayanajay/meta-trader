"""
A local, self-contained implementation of common technical indicators.
This module removes the dependency on the `pandas-ta` library, providing
more control and stability.
"""
import pandas as pd
from typing import Optional

__all__ = ["sma", "ema", "rsi", "macd", "bbands", "kc", "adx"]


def sma(series: pd.Series, length: int) -> Optional[pd.Series]:
    """
    Calculates the Simple Moving Average (SMA).

    Args:
        series: The pandas Series to calculate the SMA on.
        length: The rolling window period.

    Returns:
        A pandas Series containing the SMA, or None if input is invalid.
    """
    if not isinstance(series, pd.Series) or series.empty:
        return None
    if not isinstance(length, int) or length <= 0:
        return None
    if len(series) < length:
        return None

    return series.rolling(window=length, min_periods=length).mean()


def ema(series: pd.Series, length: int) -> Optional[pd.Series]:
    """
    Calculates the Exponential Moving Average (EMA).

    Args:
        series: The pandas Series to calculate the EMA on.
        length: The smoothing period.

    Returns:
        A pandas Series containing the EMA, or None if input is invalid.
    """
    if not isinstance(series, pd.Series) or series.empty:
        return None
    if not isinstance(length, int) or length <= 0:
        return None
    if len(series) < length:
        return None

    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def rsi(series: pd.Series, length: int = 14) -> Optional[pd.Series]:
    """
    Calculates the Relative Strength Index (RSI).

    Args:
        series: The pandas Series to calculate the RSI on (usually close prices).
        length: The period for RSI calculation.

    Returns:
        A pandas Series containing the RSI, or None if input is invalid.
    """
    if not isinstance(series, pd.Series) or series.empty:
        return None
    if not isinstance(length, int) or length <= 0:
        return None
    if len(series) < length:
        return None

    # Calculate price differences
    delta = series.diff()

    # Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Calculate smoothed average gains and losses using EMA
    avg_gain = gain.ewm(com=length - 1, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(com=length - 1, min_periods=length, adjust=False).mean()

    # Calculate Relative Strength (RS)
    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, 1e-9)

    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    return rsi


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Optional[pd.DataFrame]:
    """
    Calculates the Moving Average Convergence Divergence (MACD).

    Args:
        series: The pandas Series to calculate MACD on.
        fast: The period for the fast EMA.
        slow: The period for the slow EMA.
        signal: The period for the signal line EMA.

    Returns:
        A pandas DataFrame with MACD, histogram, and signal lines, or None.
    """
    if not isinstance(series, pd.Series) or series.empty:
        return None
    min_length = fast + slow + signal
    if len(series) < min_length:
        return None

    # Calculate the fast and slow EMAs
    ema_fast = series.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = series.ewm(span=slow, adjust=False, min_periods=slow).mean()

    # Calculate the MACD line
    macd_line = ema_fast - ema_slow

    # Calculate the signal line
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()

    # Calculate the histogram
    histogram = macd_line - signal_line

    # Create a DataFrame
    df = pd.DataFrame({
        "MACD": macd_line,
        "MACDh": histogram,
        "MACDs": signal_line,
    })
    return df


def bbands(
    series: pd.Series,
    length: int = 20,
    std: float = 2.0,
) -> Optional[pd.DataFrame]:
    """
    Calculates Bollinger Bands.

    Args:
        series: The pandas Series to calculate Bollinger Bands on.
        length: The moving average period.
        std: The number of standard deviations.

    Returns:
        A pandas DataFrame with lower, middle, and upper bands, or None.
    """
    if not isinstance(series, pd.Series) or series.empty:
        return None
    if len(series) < length:
        return None

    # Calculate the middle band (SMA)
    middle_band = series.rolling(window=length, min_periods=length).mean()

    # Calculate the standard deviation
    std_dev = series.rolling(window=length, min_periods=length).std()

    # Calculate the upper and lower bands
    upper_band = middle_band + (std_dev * std)
    lower_band = middle_band - (std_dev * std)

    df = pd.DataFrame({
        "BBL": lower_band,
        "BBM": middle_band,
        "BBU": upper_band,
    })
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> Optional[pd.Series]:
    """Helper to calculate Average True Range (ATR)."""
    if not all(isinstance(s, pd.Series) for s in [high, low, close]):
        return None

    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    return tr.ewm(com=length - 1, min_periods=length, adjust=False).mean()


def kc(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 20,
    scalar: float = 2.0,
    mamode: str = "ema"
) -> Optional[pd.DataFrame]:
    """
    Calculates Keltner Channels (KC).

    Args:
        high: The high price series.
        low: The low price series.
        close: The close price series.
        length: The period for the middle line and ATR.
        scalar: The multiplier for the ATR.
        mamode: The moving average mode for the middle line ('sma' or 'ema').

    Returns:
        A pandas DataFrame with lower, middle, and upper channel lines, or None.
    """
    if not all(isinstance(s, pd.Series) for s in [high, low, close]):
        return None
    if len(close) < length:
        return None

    # Calculate middle line
    if mamode.lower() == "sma":
        middle_line = sma(close, length)
    else:
        middle_line = ema(close, length)

    if middle_line is None:
        return None

    # Calculate ATR
    atr_series = _atr(high, low, close, length)
    if atr_series is None:
        return None

    # Calculate bands
    upper_band = middle_line + (atr_series * scalar)
    lower_band = middle_line - (atr_series * scalar)

    df = pd.DataFrame({
        "KCL": lower_band,
        "KCM": middle_line,
        "KCU": upper_band,
    })
    return df


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 14,
    lensig: int = 14,
    scalar: float = 100.0,
) -> Optional[pd.DataFrame]:
    """
    Calculates the Average Directional Movement Index (ADX).

    Args:
        high: The high price series.
        low: The low price series.
        close: The close price series.
        length: The period for the Directional Movement indicators.
        lensig: The period for the ADX line smoothing.
        scalar: The scalar multiplier.

    Returns:
        A pandas DataFrame with ADX, DMP (+DI), and DMN (-DI) lines, or None.
    """
    if not all(isinstance(s, pd.Series) for s in [high, low, close]):
        return None
    min_length = length + lensig
    if len(close) < min_length:
        return None

    # Calculate ATR
    atr_series = _atr(high, low, close, length)
    if atr_series is None:
        return None

    # Calculate Directional Movement
    up = high - high.shift(1)
    dn = low.shift(1) - low

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    pos = pos.fillna(0)
    neg = neg.fillna(0)

    # Calculate Smoothed Directional Movement (+DI and -DI)
    k = scalar / atr_series.replace(0, 1e-9)
    dmp = k * ema(pos, length=length) # +DI
    dmn = k * ema(neg, length=length) # -DI

    if dmp is None or dmn is None:
        return None

    # Calculate Directional Index (DX)
    dx_sum = (dmp + dmn).replace(0, 1e-9)
    dx = scalar * (dmp - dmn).abs() / dx_sum

    # Calculate ADX
    adx_line = ema(dx, length=lensig)
    if adx_line is None:
        return None

    df = pd.DataFrame({
        "ADX": adx_line,
        "DMP": dmp,
        "DMN": dmn,
    })
    return df
