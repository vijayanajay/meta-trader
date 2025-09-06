import pandas as pd
import pytest
import numpy as np

from praxis_engine.core.features import calculate_market_features


@pytest.fixture
def sample_market_data():
    """Creates a sample market data dictionary for testing."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=210, freq="D"))

    # Nifty data: 200 days of 100, then 10 days of 110
    nifty_prices = [100.0] * 200 + [110.0] * 10
    nifty_df = pd.DataFrame({"Close": nifty_prices}, index=dates)

    # VIX data: simple increasing series
    vix_prices = np.arange(10, 10 + len(dates), dtype=float)
    vix_df = pd.DataFrame({"Close": vix_prices}, index=dates)

    return {
        "^NSEI": nifty_df,
        "^INDIAVIX": vix_df,
    }


def test_calculate_market_features_success(sample_market_data):
    """
    Tests successful calculation of market features.
    """
    nifty_ticker = "^NSEI"
    vix_ticker = "^INDIAVIX"

    features_df = calculate_market_features(sample_market_data, nifty_ticker, vix_ticker)

    # --- Assertions ---
    assert isinstance(features_df, pd.DataFrame)
    assert list(features_df.columns) == ["nifty_vs_200ma", "vix_level", "vix_roc_10d"]
    assert len(features_df) == 210

    # Check for NaNs at the beginning due to rolling windows
    assert features_df["nifty_vs_200ma"].iloc[:199].isnull().all()
    assert not features_df["nifty_vs_200ma"].iloc[199:].isnull().any()
    assert features_df["vix_roc_10d"].iloc[:10].isnull().all()
    assert not features_df["vix_roc_10d"].iloc[10:].isnull().any()

    # --- Check specific calculated values for the last day ---
    last_day = features_df.index[-1]

    # Expected nifty_vs_200ma for the last day
    # Window for index 209 includes indices 10 through 209.
    # This window has 190 days of 100.0 and 10 days of 110.0.
    expected_sma = ((190 * 100.0) + (10 * 110.0)) / 200.0  # 100.5
    expected_nifty_ratio = 110.0 / expected_sma
    assert features_df.loc[last_day, "nifty_vs_200ma"] == pytest.approx(expected_nifty_ratio)

    # Expected vix_level for the last day
    expected_vix_level = 10.0 + 209.0
    assert features_df.loc[last_day, "vix_level"] == pytest.approx(expected_vix_level)

    # Expected vix_roc_10d for the last day
    # price[209] = 10 + 209 = 219. price[199] = 10 + 199 = 209.
    vix_today = 10.0 + 209.0
    vix_10_days_ago = 10.0 + 199.0
    expected_vix_roc = (vix_today - vix_10_days_ago) / vix_10_days_ago
    assert features_df.loc[last_day, "vix_roc_10d"] == pytest.approx(expected_vix_roc)


def test_calculate_market_features_missing_nifty(sample_market_data):
    """
    Tests that a ValueError is raised if the Nifty ticker is not in the data.
    """
    with pytest.raises(ValueError, match="Nifty ticker 'MISSING_NIFTY' not found in market_data."):
        calculate_market_features(sample_market_data, "MISSING_NIFTY", "^INDIAVIX")


def test_calculate_market_features_missing_vix(sample_market_data):
    """
    Tests that a ValueError is raised if the VIX ticker is not in the data.
    """
    with pytest.raises(ValueError, match="VIX ticker 'MISSING_VIX' not found in market_data."):
        calculate_market_features(sample_market_data, "^NSEI", "MISSING_VIX")
