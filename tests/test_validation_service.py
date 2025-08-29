"""
Integration tests for the ValidationService.
"""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from praxis_engine.core.models import (
    ScoringConfig,
    StrategyParamsConfig,
    Signal,
    ValidationScores,
)
from praxis_engine.services.validation_service import ValidationService


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
    return Signal(
        entry_price=100,
        stop_loss=98,
        exit_target_days=10,
        frames_aligned=["daily"],
        sector_vol=15.0,
    )


@patch("praxis_engine.services.validation_service.StatGuard")
@patch("praxis_engine.services.validation_service.RegimeGuard")
@patch("praxis_engine.services.validation_service.LiquidityGuard")
def test_validation_service_aggregation(
    mock_liquidity_guard_cls: MagicMock,
    mock_regime_guard_cls: MagicMock,
    mock_stat_guard_cls: MagicMock,
    scoring_config: ScoringConfig,
    strategy_params: StrategyParamsConfig,
    sample_signal: Signal,
):
    """
    Test that the ValidationService correctly calls each guard
    and aggregates their scores into a ValidationScores object.
    """
    # Arrange: Set the return scores for the mocked guards' validate methods
    mock_liquidity_guard = mock_liquidity_guard_cls.return_value
    mock_liquidity_guard.validate.return_value = 0.8

    mock_regime_guard = mock_regime_guard_cls.return_value
    mock_regime_guard.validate.return_value = 0.6

    mock_stat_guard = mock_stat_guard_cls.return_value
    mock_stat_guard.validate.return_value = 0.9

    # Act: Instantiate the service (which will use the mocked guard classes)
    # and call the validate method.
    validation_service = ValidationService(scoring=scoring_config, params=strategy_params)
    df = pd.DataFrame({"Close": [100]}, index=[pd.to_datetime("2023-01-01")])
    result = validation_service.validate(df, sample_signal)

    # Assert: Check that the result is a ValidationScores object with the correct scores
    assert isinstance(result, ValidationScores)
    assert result.liquidity_score == 0.8
    assert result.regime_score == 0.6
    assert result.stat_score == 0.9

    # Assert: Check that each guard's validate method was called exactly once
    mock_liquidity_guard.validate.assert_called_once_with(df, sample_signal)
    mock_regime_guard.validate.assert_called_once_with(df, sample_signal)
    mock_stat_guard.validate.assert_called_once_with(df, sample_signal)
