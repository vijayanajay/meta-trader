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
from praxis_engine.services.regime_model_service import RegimeModelService


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
        bb_weekly_length=10,
        bb_weekly_std=2.5,
        bb_monthly_length=6,
        bb_monthly_std=3.0,
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

def create_test_df(days: int, close_price: float, volume: float, add_market_features: bool = True) -> pd.DataFrame:
    """Creates a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D'))
    data = {
        "Close": np.full(days, close_price),
        "Volume": np.full(days, volume),
    }
    if add_market_features:
        data["nifty_vs_200ma"] = np.full(days, 1.1)
        data["vix_level"] = np.full(days, 15.0)
        data["vix_roc_10d"] = np.full(days, 0.05)

    return pd.DataFrame(data, index=dates)

# --- LiquidityGuard Tests ---

def test_liquidity_guard_scoring(scoring_config: ScoringConfig, strategy_params: StrategyParamsConfig, sample_signal: Signal) -> None:
    """Test the linear scoring of the LiquidityGuard."""
    guard = LiquidityGuard(scoring=scoring_config, params=strategy_params)
    df_min = create_test_df(days=200, close_price=1000, volume=25_000)
    current_index = len(df_min) - 1

    # Test case 1: Turnover is at the minimum, score should be 0.0
    assert guard.validate(df_min, current_index, sample_signal) == pytest.approx(0.0)

    # Test case 2: Turnover is at the maximum, score should be 1.0
    df_max = create_test_df(days=200, close_price=1000, volume=100_000)
    assert guard.validate(df_max, current_index, sample_signal) == pytest.approx(1.0)

    # Test case 3: Turnover is in the middle, score should be 0.5
    df_mid = create_test_df(days=200, close_price=1000, volume=62_500)
    assert guard.validate(df_mid, current_index, sample_signal) == pytest.approx(0.5)

# --- RegimeGuard Tests ---

@pytest.fixture
def mock_regime_service() -> MagicMock:
    """Fixture for a mocked RegimeModelService."""
    return MagicMock(spec=RegimeModelService)

def test_regime_guard_uses_model_score(scoring_config: ScoringConfig, sample_signal: Signal, mock_regime_service: MagicMock) -> None:
    """Test that the RegimeGuard correctly uses a non-neutral score from the model."""
    # Arrange
    mock_regime_service.predict_proba.return_value = 0.75
    guard = RegimeGuard(scoring=scoring_config, regime_model_service=mock_regime_service)
    df = create_test_df(days=200, close_price=100, volume=1_000_000)
    current_index = len(df) - 1
    model_features = ["nifty_vs_200ma", "vix_level", "vix_roc_10d"]

    # Act
    score = guard.validate(df, current_index, sample_signal)

    # Assert
    assert score == 0.75
    mock_regime_service.predict_proba.assert_called_once()
    call_args, _ = mock_regime_service.predict_proba.call_args
    passed_df = call_args[0]
    expected_df = df.iloc[[current_index]][model_features]
    pd.testing.assert_frame_equal(passed_df, expected_df)

def test_regime_guard_falls_back_to_sector_vol(scoring_config: ScoringConfig, sample_signal: Signal, mock_regime_service: MagicMock) -> None:
    """Test that the RegimeGuard falls back to sector volatility when the model is neutral."""
    # Arrange
    mock_regime_service.predict_proba.return_value = 1.0  # Neutral score
    guard = RegimeGuard(scoring=scoring_config, regime_model_service=mock_regime_service)
    df = create_test_df(days=200, close_price=100, volume=1_000_000)
    current_index = len(df) - 1
    sample_signal.sector_vol = 17.5 # Midpoint volatility

    # Act
    score = guard.validate(df, current_index, sample_signal)

    # Assert
    # Expected score: linear interpolation between 10% vol (score 1.0) and 25% vol (score 0.0)
    # Midpoint is 17.5, so score should be 0.5
    assert score == pytest.approx(0.5)
    mock_regime_service.predict_proba.assert_called_once()

def test_regime_guard_handles_missing_features(scoring_config: ScoringConfig, sample_signal: Signal, mock_regime_service: MagicMock) -> None:
    """Test that the guard falls back if market features are missing."""
    # Arrange
    guard = RegimeGuard(scoring=scoring_config, regime_model_service=mock_regime_service)
    df = create_test_df(days=200, close_price=100, volume=1_000_000, add_market_features=False)
    current_index = len(df) - 1
    sample_signal.sector_vol = 10.0 # Should result in a perfect fallback score

    # Act
    score = guard.validate(df, current_index, sample_signal)

    # Assert
    assert score == pytest.approx(1.0)
    # The predict method should not be called if features are missing
    mock_regime_service.predict_proba.assert_not_called()


# --- StatGuard Tests ---

def test_stat_guard_scoring(scoring_config: ScoringConfig, strategy_params: StrategyParamsConfig, sample_signal: Signal) -> None:
    """Test the geometric mean scoring of the StatGuard based on pre-computed columns."""
    guard = StatGuard(scoring=scoring_config, params=strategy_params)
    df = create_test_df(days=200, close_price=100, volume=1_000_000, add_market_features=False)
    current_index = len(df) - 1

    hurst_col = f"hurst_{strategy_params.hurst_length}"
    adf_col = "adf_p_value"

    # Test case 1: Both stats are perfect, final score is 1.0
    df[hurst_col] = 0.30
    df[adf_col] = 0.00
    assert guard.validate(df, current_index, sample_signal) == pytest.approx(1.0)

    # Test case 2: Both stats are at the worst acceptable level, final score is 0.0
    df[hurst_col] = 0.45
    df[adf_col] = 0.05
    assert guard.validate(df, current_index, sample_signal) == pytest.approx(0.0)

    # Test case 5: Both scores are 0.5, final score is sqrt(0.5*0.5) = 0.5
    df[hurst_col] = 0.375 # Midpoint for hurst
    df[adf_col] = 0.025 # Midpoint for p-value
    assert guard.validate(df, current_index, sample_signal) == pytest.approx(0.5)
