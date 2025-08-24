"""
Unit tests for the core statistics library.
"""
import numpy as np
import pandas as pd
import pytest

from praxis_engine.core.statistics import adf_test, hurst_exponent


@pytest.fixture
def mean_reverting_series() -> pd.Series:
    """A deterministic mean-reverting series (sine wave)."""
    return pd.Series(np.sin(np.linspace(0, 20 * np.pi, 200)))


@pytest.fixture
def trending_series() -> pd.Series:
    """A deterministic trending series."""
    return pd.Series(np.arange(200) * 0.1)


def test_adf_test_values(mean_reverting_series: pd.Series, trending_series: pd.Series) -> None:
    """Test adf_test with known series."""
    # Mean-reverting series should have a small p-value
    p_value_mr = adf_test(mean_reverting_series)
    assert p_value_mr is not None
    assert p_value_mr < 0.05

    # Trending series should have a large p-value
    p_value_trend = adf_test(trending_series)
    assert p_value_trend is not None
    assert p_value_trend > 0.05


def test_adf_test_empty() -> None:
    """Test adf_test with an empty series."""
    assert adf_test(pd.Series([], dtype=float)) is None


def test_hurst_exponent_values(mean_reverting_series: pd.Series, trending_series: pd.Series) -> None:
    """Test hurst_exponent with known series."""
    # Mean-reverting series should have H < 0.5
    h_mr = hurst_exponent(mean_reverting_series)
    assert h_mr is not None
    assert h_mr < 0.5

    # Trending series should have H > 0.5
    h_trend = hurst_exponent(trending_series)
    assert h_trend is not None
    assert h_trend > 0.6


def test_hurst_exponent_short_series() -> None:
    """Test hurst_exponent with a series that is too short."""
    short_series = pd.Series(np.random.randn(50))
    assert hurst_exponent(short_series) is None
