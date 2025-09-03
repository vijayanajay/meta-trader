"""
Unit tests for the SignalEngine.
"""
import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from typing import Any, Dict, List

from praxis_engine.core.models import StrategyParamsConfig, SignalLogicConfig, Signal
from praxis_engine.services.signal_engine import SignalEngine

@pytest.fixture
def strategy_params() -> StrategyParamsConfig:
    """Fixture for default strategy parameters."""
    return StrategyParamsConfig(
        bb_length=20,
        bb_std=2.0,
        rsi_length=14,
        hurst_length=100,
        exit_days=10,
        min_history_days=200,
        liquidity_lookback_days=5,
    )

@pytest.fixture
def signal_logic_config() -> SignalLogicConfig:
    """Fixture for default signal logic configuration."""
    return SignalLogicConfig(
        require_daily_oversold=True,
        require_weekly_oversold=True,
        require_monthly_not_oversold=True,
        rsi_threshold=30,
    )

@pytest.fixture
def signal_engine(
    strategy_params: StrategyParamsConfig, signal_logic_config: SignalLogicConfig
) -> SignalEngine:
    """Fixture for SignalEngine."""
    return SignalEngine(params=strategy_params, logic=signal_logic_config)


def test_generate_signal_logic_success(signal_engine: SignalEngine, strategy_params: StrategyParamsConfig) -> None:
    """
    Tests the core alignment logic of generate_signal by feeding it a
    dataframe with pre-computed indicators.
    """
    # --- Arrange ---
    # Create a dataframe with enough data to pass the length checks
    num_rows = strategy_params.bb_length + 5
    dates = pd.to_datetime(pd.date_range(end='2023-01-15', periods=num_rows, freq='D'))

    data = {
        'Close': np.full(num_rows, 100.0),
        'BBL_20_2.0': np.full(num_rows, 105.0),
        'BBM_20_2.0': np.full(num_rows, 110.0),
        'RSI_14': np.full(num_rows, 40.0),
        'BBL_10_2.5': np.full(num_rows, 108.0),
        'BBL_6_3.0': np.full(num_rows, 115.0),
        'sector_vol': np.full(num_rows, 0.15)
    }
    df = pd.DataFrame(data, index=dates)

    # Overwrite the last row with data that will trigger a signal
    signal_index = num_rows - 1
    df.loc[df.index[signal_index], 'Close'] = 75.0
    df.loc[df.index[signal_index], 'BBL_20_2.0'] = 80.0
    df.loc[df.index[signal_index], 'BBM_20_2.0'] = 90.0
    df.loc[df.index[signal_index], 'RSI_14'] = 25.0
    df.loc[df.index[signal_index], 'BBL_10_2.5'] = 85.0
    df.loc[df.index[signal_index], 'BBL_6_3.0'] = 70.0 # Close > BBL for 'not oversold'

    # --- Act ---
    signal = signal_engine.generate_signal(df, signal_index)

    # --- Assert ---
    assert isinstance(signal, Signal)
    assert signal.entry_price > 75.0
    assert signal.stop_loss == 90.0
