"""
Unit tests for the core indicators library.
"""
import numpy as np
import pandas as pd
import pytest

from praxis_engine.core.indicators import bbands, rsi


@pytest.fixture
def sample_series() -> pd.Series:
    """A deterministic pandas Series for testing."""
    data = [
        50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 54.0, 53.0, 52.0, 51.0,
        50.0, 49.0, 48.0, 47.0, 46.0, 45.0, 46.0, 47.0, 48.0, 49.0,
        50.0, 51.0, 52.0, 53.0, 54.0
    ]
    return pd.Series(data, name="close")

def test_bbands_values(sample_series: pd.Series) -> None:
    """Test the bbands function with known values."""
    result = bbands(sample_series, length=20, std=2.0)
    assert result is not None
    # Recalculate expected values based on the correct BBM of 50.0
    # Last 20 values from fixture: 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54
    # The sample series has 25 elements. The last 20 are from index 5 to 24.
    # The mean is correct, it's 50.0.
    # The std of the last 20 elements is calculated below.
    last_20 = sample_series.iloc[5:]
    expected_std = last_20.std()
    expected_bbm = 50.0
    expected_bbl = expected_bbm - 2 * expected_std
    expected_bbu = expected_bbm + 2 * expected_std

    assert isinstance(result, pd.DataFrame)
    # Check last row for specific calculated values
    assert np.isclose(result["BBM_20_2.0"].iloc[-1], expected_bbm)
    assert np.isclose(result["BBL_20_2.0"].iloc[-1], expected_bbl)
    assert np.isclose(result["BBU_20_2.0"].iloc[-1], expected_bbu)


def test_bbands_empty() -> None:
    """Test bbands with an empty series."""
    empty_series = pd.Series([], dtype=float)
    assert bbands(empty_series) is None


def test_bbands_short() -> None:
    """Test bbands with a short series."""
    short_series = pd.Series(np.random.rand(10), dtype=float)
    assert bbands(short_series, length=20) is None


def test_rsi_values(sample_series: pd.Series) -> None:
    """Test the rsi function with known values."""
    result = rsi(sample_series, length=14)
    assert result is not None
    assert isinstance(result, pd.Series)
    # Check last row for specific calculated value
    assert np.isclose(result.iloc[-1], 64.2857, atol=1e-4)


def test_rsi_empty() -> None:
    """Test rsi with an empty series."""
    empty_series = pd.Series([], dtype=float)
    assert rsi(empty_series) is None


def test_rsi_short() -> None:
    """Test rsi with a short series."""
    short_series = pd.Series(np.random.rand(10), dtype=float)
    assert rsi(short_series, length=14) is None
