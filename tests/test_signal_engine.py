"""
Unit tests for the SignalEngine.
"""
import pandas as pd
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

def create_test_dataframe(data: Dict[str, List[Any]], index: List[Any]) -> pd.DataFrame:
    """Helper to create a dataframe for testing."""
    return pd.DataFrame(data, index=pd.to_datetime(index))

@patch('praxis_engine.services.signal_engine.SignalEngine._prepare_dataframes')
def test_generate_signal_logic_success(
    mock_prepare_dataframes: MagicMock, signal_engine: SignalEngine
) -> None:
    """
    Tests the core alignment logic of generate_signal by feeding it
    perfectly crafted dataframes, bypassing the preparation step.
    """
    # --- Arrange ---
    # Create handcrafted dataframes that will force the signal to fire
    last_date = '2023-01-15'

    df_daily = create_test_dataframe({
        'Close': [75.0],
        'BBL_20_2.0': [80.0],
        'BBM_20_2.0': [90.0],
        'RSI_14': [25.0],
        'sector_vol': [0.15]
    }, [last_date])

    df_weekly = create_test_dataframe({
        'Close': [85.0],
        'BBL_10_2.5': [90.0],
    }, [pd.to_datetime(last_date) - pd.Timedelta(days=1)]) # To simulate asof

    df_monthly = create_test_dataframe({
        'Close': [95.0],
        'BBL_6_3.0': [90.0], # Close > BBL for 'not oversold'
    }, [pd.to_datetime(last_date) - pd.Timedelta(days=10)]) # To simulate asof

    mock_prepare_dataframes.return_value = (df_daily, df_weekly, df_monthly)

    # This initial dataframe is now just a dummy since we mock the prep method
    dummy_df = pd.DataFrame(index=pd.date_range(end=last_date, periods=30))

    # --- Act ---
    signal = signal_engine.generate_signal(dummy_df)

    # --- Assert ---
    assert isinstance(signal, Signal)
    assert signal.entry_price > 75.0
    assert signal.stop_loss == 90.0
    mock_prepare_dataframes.assert_called_once()

def test_prepare_dataframes(signal_engine: SignalEngine) -> None:
    """
    Tests the data preparation method to ensure it processes data correctly.
    This is now an integration test for the preparation step.
    """
    # --- Arrange ---
    # Create a realistic-looking dataframe
    dates = pd.to_datetime(pd.date_range(end='2023-01-15', periods=200, freq='D'))
    df = pd.DataFrame({
        "Close": 100 + pd.Series(range(200), index=dates) * 0.1,
        "Volume": 1_000_000,
        "sector_vol": 0.15,
    }, index=dates)

    # Make the last day have a sharp drop to ensure there's some volatility
    df.iloc[-1, df.columns.get_loc('Close')] = 80

    # --- Act ---
    result = signal_engine._prepare_dataframes(df)

    # --- Assert ---
    assert result is not None
    df_daily, df_weekly, df_monthly = result

    # Check daily frame
    assert not df_daily.empty
    assert f"BBL_{signal_engine.params.bb_length}_{signal_engine.params.bb_std}" in df_daily.columns
    assert f"RSI_{signal_engine.params.rsi_length}" in df_daily.columns

    # Check weekly frame
    assert not df_weekly.empty
    assert "BBL_10_2.5" in df_weekly.columns

    # Check monthly frame
    assert not df_monthly.empty
    assert "BBL_6_3.0" in df_monthly.columns
