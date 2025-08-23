"""
Unit tests for the core statistics library.
"""
import numpy as np
import pandas as pd
import pytest

from praxis_engine.core.statistics import adf_test, hurst_exponent


@pytest.fixture
def stationary_series() -> pd.Series:
    """A stationary series for testing."""
    return pd.Series(np.random.randn(150))


@pytest.fixture
def non_stationary_series() -> pd.Series:
    """A non-stationary (trending) series for testing."""
    return pd.Series(np.arange(150) + np.random.randn(150) * 0.1)


def test_adf_test_stationary(stationary_series: pd.Series) -> None:
    """Test adf_test with a stationary series."""
    p_value = adf_test(stationary_series)
    assert p_value is not None
    assert p_value < 0.05


def test_adf_test_non_stationary(non_stationary_series: pd.Series) -> None:
    """Test adf_test with a non-stationary series."""
    p_value = adf_test(non_stationary_series)
    assert p_value is not None
    assert p_value > 0.05


def test_adf_test_empty() -> None:
    """Test adf_test with an empty series."""
    assert adf_test(pd.Series([], dtype=float)) is None


def test_hurst_exponent_random_walk(stationary_series: pd.Series) -> None:
    """Test hurst_exponent with a random walk series."""
    # A random walk is the cumulative sum of a stationary series
    random_walk = stationary_series.cumsum()
    h = hurst_exponent(random_walk)
    assert h is not None
    # Should be close to 0.5, but with some variance
    assert 0.3 < h < 0.8


def test_hurst_exponent_trending(non_stationary_series: pd.Series) -> None:
    """Test hurst_exponent with a trending series."""
    h = hurst_exponent(non_stationary_series)
    assert h is not None
    assert h > 0.8 # Trending series should have a high Hurst exponent


def test_hurst_exponent_short_series() -> None:
    """Test hurst_exponent with a series that is too short."""
    short_series = pd.Series(np.random.randn(50))
    assert hurst_exponent(short_series) is None
