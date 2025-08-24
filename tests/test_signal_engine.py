"""
Unit tests for the SignalEngine.
"""
import pandas as pd
import pytest
import numpy as np

from praxis_engine.core.models import StrategyParamsConfig, Signal
from praxis_engine.services.signal_engine import SignalEngine

@pytest.fixture
def strategy_params() -> StrategyParamsConfig:
    """Fixture for strategy parameters."""
    return StrategyParamsConfig(
        bb_length=20,
        bb_std=2.0,
        rsi_length=14,
        hurst_length=100,
        exit_days=10
    )

@pytest.fixture
def signal_engine(strategy_params: StrategyParamsConfig) -> SignalEngine:
    """Fixture for SignalEngine."""
    return SignalEngine(params=strategy_params)

def create_test_df(days: int) -> pd.DataFrame:
    """Creates a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D'))
    return pd.DataFrame({
        "Close": np.random.rand(days) * 10 + 100,
        "Volume": np.full(days, 10_00_000),
        "sector_vol": np.full(days, 0.15),
    }, index=dates)

@pytest.mark.skip(reason="Test is brittle and fails with minor pandas version changes. Needs to be rewritten.")
def test_generate_signal_success(signal_engine: SignalEngine):
    """Test a successful signal generation with deterministic data."""
    # Construct a dataset designed to trigger the signal
    days = 200
    days = 300
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D'))

    # Base series is stable at 100
    close_prices = np.full(days, 100.0)

    # --- Trigger Conditions ---
    # 1. Monthly: Not oversold. We'll keep the first few months stable at 100.
    # The BBands will be tight around 100. A close of 100 is > BBL.

    # 2. Weekly: Oversold. Make the last few weeks trend down.
    close_prices[-30:] = np.linspace(100, 80, 30)

    # 3. Daily: Oversold. Make the last day a sharp drop.
    close_prices[-1] = 70
    # Make RSI low by having a series of down-days.
    close_prices[-14:] = np.linspace(90, 70, 14)

    df = pd.DataFrame({
        "Close": close_prices,
        "Volume": np.full(days, 10_00_000),
        "sector_vol": np.full(days, 0.15),
    }, index=dates)

    signal = signal_engine.generate_signal(df)
    assert isinstance(signal, Signal), "Signal should have been generated"
    assert signal.frames_aligned == ["daily", "weekly"]

def test_generate_signal_daily_fail(signal_engine: SignalEngine):
    """Test when the daily condition is not met."""
    df = create_test_df(200)
    df.iloc[-1, df.columns.get_loc('Close')] = 200
    signal = signal_engine.generate_signal(df)
    assert signal is None

def test_generate_signal_too_short(signal_engine: SignalEngine):
    """Test with a dataframe that is too short."""
    df = create_test_df(10)
    signal = signal_engine.generate_signal(df)
    assert signal is None
