import pytest
from unittest.mock import patch, MagicMock, call
import copy
import numpy as np

from praxis_engine.core.orchestrator import Orchestrator, _set_nested_attr
from praxis_engine.core.models import Config, DataConfig, StrategyParamsConfig, FiltersConfig, ScoringConfig, SignalLogicConfig, LLMConfig, CostModelConfig, ExitLogicConfig, SensitivityAnalysisConfig, BacktestSummary

# A minimal, valid config for testing
@pytest.fixture
def base_config() -> Config:
    return Config(
        data=DataConfig(cache_dir="test", stocks_to_backtest=["TEST.NS"], start_date="2022-01-01", end_date="2022-12-31", sector_map={"TEST.NS": "^NSEI"}),
        strategy_params=StrategyParamsConfig(bb_length=20, bb_std=2, rsi_length=14, hurst_length=100, exit_days=20, min_history_days=200, liquidity_lookback_days=5),
        filters=FiltersConfig(sector_vol_threshold=22.0, liquidity_turnover_crores=5.0, adf_p_value_threshold=0.05, hurst_threshold=0.45),
        scoring=ScoringConfig(
            liquidity_score_min_turnover_crores=2.5,
            liquidity_score_max_turnover_crores=10.0,
            regime_score_min_volatility_pct=25.0,
            regime_score_max_volatility_pct=10.0,
            hurst_score_min_h=0.45,
            hurst_score_max_h=0.30,
            adf_score_min_pvalue=0.05,
            adf_score_max_pvalue=0.00,
        ),
        signal_logic=SignalLogicConfig(require_daily_oversold=True, require_weekly_oversold=False, require_monthly_not_oversold=True, rsi_threshold=35),
        llm=LLMConfig(provider="test", confidence_threshold=0.7, min_composite_score_for_llm=0.1, model="test", prompt_template_path="test"),
        cost_model=CostModelConfig(brokerage_rate=0.0003, brokerage_max=20, stt_rate=0.00025, assumed_trade_value_inr=100000, slippage_volume_threshold=100000, slippage_rate_high_liquidity=0.0005, slippage_rate_low_liquidity=0.001),
        exit_logic=ExitLogicConfig(use_atr_exit=True, atr_period=14, atr_stop_loss_multiplier=2.5, max_holding_days=40),
    )

@patch('praxis_engine.core.orchestrator.Orchestrator.run_backtest')
def test_run_sensitivity_analysis_efficient(mock_run_backtest: MagicMock, base_config: Config) -> None:
    """
    Tests the refactored, efficient implementation of run_sensitivity_analysis.
    It should now call run_backtest on the *same* instance, not create new ones.
    """
    # Setup sensitivity analysis config
    base_config.sensitivity_analysis = SensitivityAnalysisConfig(
        parameter_to_vary="filters.sector_vol_threshold",
        start_value=20.0,
        end_value=22.0,  # smaller range for test brevity
        step_size=1.0
    )
    orchestrator = Orchestrator(config=base_config)
    mock_run_backtest.return_value = []  # Each backtest run returns no trades

    # Act
    orchestrator.run_sensitivity_analysis()

    # Assert
    # Expected values: 20.0, 21.0, 22.0 -> 3 calls to run_backtest
    # Each call is for the one stock in the config, so 3 calls total.
    assert mock_run_backtest.call_count == 3


def test_set_nested_attr() -> None:
    """
    Tests the helper function for setting nested attributes.
    """
    class Inner:
        b: int = 1
        c: int # Declare attribute for mypy

    class Outer:
        a: Inner = Inner()

    obj = Outer()
    _set_nested_attr(obj, "a.b", 99)
    assert obj.a.b == 99

    # setattr creates the attribute if it doesn't exist.
    # We test this behavior and satisfy mypy by pre-declaring 'c'.
    _set_nested_attr(obj.a, "c", 101)
    assert obj.a.c == 101
