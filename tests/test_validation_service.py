"""
Unit tests for the ValidationService.
"""
import pandas as pd
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path

from praxis_engine.core.models import FiltersConfig, Signal, StrategyParamsConfig, ValidationResult
from praxis_engine.services.validation_service import ValidationService

@pytest.fixture
def filters_config() -> FiltersConfig:
    """Fixture for filters configuration."""
    return FiltersConfig(
        sector_vol_threshold=22.0,
        liquidity_turnover_crores=5.0,
        adf_p_value_threshold=0.05,
        hurst_threshold=0.5
    )

@pytest.fixture
def strategy_params() -> StrategyParamsConfig:
    """Fixture for strategy parameters."""
    return StrategyParamsConfig(bb_length=20, bb_std=2.0, rsi_length=14, hurst_length=100, exit_days=10)

@pytest.fixture
def validation_service(filters_config: FiltersConfig, strategy_params: StrategyParamsConfig) -> ValidationService:
    """Fixture for ValidationService."""
    return ValidationService(filters=filters_config, params=strategy_params)

@pytest.fixture
def sample_signal() -> Signal:
    """A sample signal for testing."""
    return Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["daily"], sector_vol=15.0)

def create_test_df(days: int, close_price: float, volume: float) -> pd.DataFrame:
    """Creates a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D'))
    # Create a more realistic series for Close so ADF test can pass
    close_prices = np.full(days, close_price) + (np.random.randn(days) * 0.1)
    return pd.DataFrame({
        "Close": close_prices,
        "Volume": np.full(days, volume),
        "sector_vol": np.full(days, 15.0),
    })

def test_validate_success(validation_service: ValidationService, sample_signal: Signal) -> None:
    """Test a successful validation where all guardrails pass."""
    # Create data that should pass: high liquidity, low vol, mean-reverting (flat series)
    df = create_test_df(days=200, close_price=100.0, volume=10_00_000) # 10Cr turnover
    result = validation_service.validate(df, sample_signal)
    assert result.is_valid is True

def test_validate_liquidity_fail(validation_service: ValidationService, sample_signal: Signal) -> None:
    """Test failure due to low liquidity."""
    df = create_test_df(days=200, close_price=100.0, volume=100) # Low turnover
    result = validation_service.validate(df, sample_signal)
    assert result.is_valid is False
    assert result.liquidity_check is False
    assert result.reason == "Low Liquidity"

def test_validate_regime_fail(validation_service: ValidationService, sample_signal: Signal) -> None:
    """Test failure due to high sector volatility."""
    df = create_test_df(days=200, close_price=100.0, volume=10_00_000)
    sample_signal.sector_vol = 25.0 # High volatility
    result = validation_service.validate(df, sample_signal)
    assert result.is_valid is False
    assert result.regime_check is False
    assert result.reason == "High Sector Volatility"

@patch('praxis_engine.services.validation_service.adf_test', return_value=0.1)
def test_validate_adf_fail(mock_adf: MagicMock, validation_service: ValidationService, sample_signal: Signal) -> None:
    """Test failure due to ADF test."""
    df = create_test_df(days=200, close_price=100.0, volume=10_00_000)
    result = validation_service.validate(df, sample_signal)
    assert result.is_valid is False
    assert result.stat_check is False
    assert result.reason == "ADF test failed"

@patch('praxis_engine.services.validation_service.hurst_exponent', return_value=0.6)
def test_validate_hurst_fail(mock_hurst: MagicMock, validation_service: ValidationService, sample_signal: Signal) -> None:
    """Test failure due to Hurst exponent."""
    df = create_test_df(days=200, close_price=100.0, volume=10_00_000)
    result = validation_service.validate(df, sample_signal)
    assert result.is_valid is False
    assert result.stat_check is False
    assert result.reason == "Hurst exponent too high"
