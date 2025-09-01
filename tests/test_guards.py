"""
Unit tests for individual validation guards and their scoring logic.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from praxis_engine.core.models import ScoringConfig, StrategyParamsConfig, Signal
from praxis_engine.core.guards.liquidity_guard import LiquidityGuard
from praxis_engine.core.guards.regime_guard import RegimeGuard
from praxis_engine.core.guards.stat_guard import StatGuard

@pytest.fixture
def scoring_config() -> ScoringConfig:
    """Fixture for scoring configuration."""
    return ScoringConfig(
        liquidity_score_min_turnover_crores=2.5,
        liquidity_score_max_turnover_crores=10.0,
        regime_score_min_volatility_pct=25.0,
        regime_score_max_volatility_pct=10.0,
        hurst_score_min_h=0.45,
        hurst_score_max_h=0.30,
        adf_score_min_pvalue=0.05,
        adf_score_max_pvalue=0.00,
    )

@pytest.fixture
def strategy_params() -> StrategyParamsConfig:
    """Fixture for strategy parameters."""
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
def sample_signal() -> Signal:
    """A sample signal for testing."""
    return Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["daily"], sector_vol=15.0)

def create_test_df(days: int, close_price: float, volume: float) -> pd.DataFrame:
    """Creates a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D'))
    return pd.DataFrame({
        "Close": np.full(days, close_price),
        "Volume": np.full(days, volume),
    }, index=dates)

# --- LiquidityGuard Tests ---

def test_liquidity_guard_scoring(scoring_config: ScoringConfig, strategy_params: StrategyParamsConfig, sample_signal: Signal) -> None:
    """Test the linear scoring of the LiquidityGuard."""
    guard = LiquidityGuard(scoring=scoring_config, params=strategy_params)

    # Test case 1: Turnover is at the minimum, score should be 0.0
    # 2.5 Cr turnover = 25,000 volume at 1000 price
    df_min = create_test_df(days=200, close_price=1000, volume=25_000)
    assert guard.validate(df_min, sample_signal) == pytest.approx(0.0)

    # Test case 2: Turnover is at the maximum, score should be 1.0
    # 10 Cr turnover = 100,000 volume at 1000 price
    df_max = create_test_df(days=200, close_price=1000, volume=100_000)
    assert guard.validate(df_max, sample_signal) == pytest.approx(1.0)

    # Test case 3: Turnover is in the middle, score should be 0.5
    # 6.25 Cr turnover = 62,500 volume at 1000 price
    df_mid = create_test_df(days=200, close_price=1000, volume=62_500)
    assert guard.validate(df_mid, sample_signal) == pytest.approx(0.5)

    # Test case 4: Turnover is below min, score should be 0.0 (clamped)
    df_below = create_test_df(days=200, close_price=1000, volume=10_000)
    assert guard.validate(df_below, sample_signal) == pytest.approx(0.0)

    # Test case 5: Turnover is above max, score should be 1.0 (clamped)
    df_above = create_test_df(days=200, close_price=1000, volume=200_000)
    assert guard.validate(df_above, sample_signal) == pytest.approx(1.0)

# --- RegimeGuard Tests ---

def test_regime_guard_scoring(scoring_config: ScoringConfig, sample_signal: Signal) -> None:
    """Test the inverse linear scoring of the RegimeGuard."""
    guard = RegimeGuard(scoring=scoring_config)
    df = create_test_df(days=200, close_price=100, volume=1_000_000) # df is not used by this guard

    # Test case 1: Vol is at the minimum (high vol), score should be 0.0
    sample_signal.sector_vol = 25.0
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 2: Vol is at the maximum (low vol), score should be 1.0
    sample_signal.sector_vol = 10.0
    assert guard.validate(df, sample_signal) == pytest.approx(1.0)

    # Test case 3: Vol is in the middle, score should be 0.5
    sample_signal.sector_vol = 17.5
    assert guard.validate(df, sample_signal) == pytest.approx(0.5)

    # Test case 4: Vol is above min, score should be 0.0 (clamped)
    sample_signal.sector_vol = 30.0
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 5: Vol is below max, score should be 1.0 (clamped)
    sample_signal.sector_vol = 5.0
    assert guard.validate(df, sample_signal) == pytest.approx(1.0)

# --- StatGuard Tests ---

@patch('praxis_engine.core.guards.stat_guard.hurst_exponent')
@patch('praxis_engine.core.guards.stat_guard.adf_test')
def test_stat_guard_scoring(mock_adf: MagicMock, mock_hurst: MagicMock, scoring_config: ScoringConfig, strategy_params: StrategyParamsConfig, sample_signal: Signal) -> None:
    """Test the geometric mean scoring of the StatGuard."""
    guard = StatGuard(scoring=scoring_config, params=strategy_params)
    df = create_test_df(days=200, close_price=100, volume=1_000_000)

    # Test case 1: Both stats are perfect (p-value=0, hurst=0.3), scores are 1.0, final score is 1.0
    mock_adf.return_value = 0.00
    mock_hurst.return_value = 0.30
    assert guard.validate(df, sample_signal) == pytest.approx(1.0)

    # Test case 2: Both stats are at the worst acceptable level, scores are 0.0, final score is 0.0
    mock_adf.return_value = 0.05
    mock_hurst.return_value = 0.45
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 3: ADF is perfect (score=1.0), Hurst is worst (score=0.0), final score is 0.0
    mock_adf.return_value = 0.00
    mock_hurst.return_value = 0.45
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 4: ADF is worst (score=0.0), Hurst is perfect (score=1.0), final score is 0.0
    mock_adf.return_value = 0.05
    mock_hurst.return_value = 0.30
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 5: Both scores are 0.5, final score is sqrt(0.5*0.5) = 0.5
    mock_adf.return_value = 0.025 # Midpoint for p-value
    mock_hurst.return_value = 0.375 # Midpoint for hurst
    assert guard.validate(df, sample_signal) == pytest.approx(0.5)

    # Test case 6: Handle None from adf_test, score should be 0
    mock_adf.return_value = None
    mock_hurst.return_value = 0.30
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)

    # Test case 7: Handle None from hurst_exponent, score should be 0
    mock_adf.return_value = 0.01
    mock_hurst.return_value = None
    assert guard.validate(df, sample_signal) == pytest.approx(0.0)
