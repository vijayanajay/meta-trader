"""
Unit tests for the core indicators library.
"""
import numpy as np
import pandas as pd
import pytest

from praxis_engine.core.indicators import bbands, rsi


@pytest.fixture
def sample_series() -> pd.Series:
    """A sample pandas Series for testing."""
    return pd.Series(np.random.rand(50) * 100, name="close")


def test_bbands(sample_series: pd.Series) -> None:
    """Test the bbands function."""
    result = bbands(sample_series, length=20, std=2.0)
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert "BBL_20_2.0" in result.columns
    assert "BBM_20_2.0" in result.columns
    assert "BBU_20_2.0" in result.columns
    assert not result.isnull().all().all()
    # Check that the middle band is the moving average
    pd.testing.assert_series_equal(
        result["BBM_20_2.0"],
        sample_series.rolling(window=20).mean(),
        check_names=False,
    )


def test_bbands_empty() -> None:
    """Test bbands with an empty series."""
    empty_series = pd.Series([], dtype=float)
    assert bbands(empty_series) is None


def test_bbands_short() -> None:
    """Test bbands with a short series."""
    short_series = pd.Series(np.random.rand(10), dtype=float)
    assert bbands(short_series, length=20) is None


def test_rsi(sample_series: pd.Series) -> None:
    """Test the rsi function."""
    result = rsi(sample_series, length=14)
    assert result is not None
    assert isinstance(result, pd.Series)
    assert not result.isnull().all()


def test_rsi_empty() -> None:
    """Test rsi with an empty series."""
    empty_series = pd.Series([], dtype=float)
    assert rsi(empty_series) is None


def test_rsi_short() -> None:
    """Test rsi with a short series."""
    short_series = pd.Series(np.random.rand(10), dtype=float)
    assert rsi(short_series, length=14) is None
