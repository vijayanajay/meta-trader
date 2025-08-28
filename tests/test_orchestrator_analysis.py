import pytest
from unittest.mock import patch, MagicMock, call
import copy
import numpy as np

from praxis_engine.core.orchestrator import Orchestrator, _set_nested_attr
from praxis_engine.core.models import Config, DataConfig, StrategyParamsConfig, FiltersConfig, SignalLogicConfig, LLMConfig, CostModelConfig, ExitLogicConfig, SensitivityAnalysisConfig, BacktestSummary

# A minimal, valid config for testing
@pytest.fixture
def base_config() -> Config:
    return Config(
        data=DataConfig(cache_dir="test", stocks_to_backtest=["TEST.NS"], start_date="2022-01-01", end_date="2022-12-31", sector_map={"TEST.NS": "^NSEI"}),
        strategy_params=StrategyParamsConfig(bb_length=20, bb_std=2, rsi_length=14, hurst_length=100, exit_days=20, min_history_days=200, liquidity_lookback_days=5),
        filters=FiltersConfig(sector_vol_threshold=22.0, liquidity_turnover_crores=5.0, adf_p_value_threshold=0.05, hurst_threshold=0.45),
        signal_logic=SignalLogicConfig(require_daily_oversold=True, require_weekly_oversold=False, require_monthly_not_oversold=True, rsi_threshold=35),
        llm=LLMConfig(provider="test", confidence_threshold=0.7, model="test", prompt_template_path="test"),
        cost_model=CostModelConfig(brokerage_rate=0.0003, brokerage_max=20, stt_rate=0.00025, assumed_trade_value_inr=100000, slippage_volume_threshold=100000, slippage_rate_high_liquidity=0.0005, slippage_rate_low_liquidity=0.001),
        exit_logic=ExitLogicConfig(use_atr_exit=True, atr_period=14, atr_stop_loss_multiplier=2.5, max_holding_days=40),
    )

@patch('praxis_engine.core.orchestrator.Orchestrator')
def test_run_sensitivity_analysis(MockOrchestrator, base_config):
    # Setup sensitivity analysis config
    base_config.sensitivity_analysis = SensitivityAnalysisConfig(
        parameter_to_vary="filters.sector_vol_threshold",
        start_value=20.0,
        end_value=22.0, # smaller range for test brevity
        step_size=1.0
    )

    # The real orchestrator we are testing
    # Note: We patch the class, so this instance is the real one, but any
    # new Orchestrator created inside its method will be a mock.
    orchestrator_under_test = Orchestrator(config=base_config)

    # Mock the return value of run_backtest from the MOCKED orchestrator class
    mock_instance = MockOrchestrator.return_value
    mock_instance.run_backtest.return_value = []

    # Call the method we are testing
    orchestrator_under_test.run_sensitivity_analysis()

    # Check that a new Orchestrator was instantiated for each parameter value
    # Expected values: 20.0, 21.0, 22.0 -> 3 calls
    assert MockOrchestrator.call_count == 3

    # Check that the configs passed to the new instances were correct
    call_args_list = MockOrchestrator.call_args_list
    modified_values = [
        round(c.args[0].filters.sector_vol_threshold, 1)
        for c in call_args_list
    ]
    assert modified_values == [20.0, 21.0, 22.0]

    # Check that run_backtest was called on each mock instance
    assert mock_instance.run_backtest.call_count == 3


def test_set_nested_attr():
    """
    Tests the helper function for setting nested attributes.
    """
    class Inner(object):
        b = 1

    class Outer(object):
        a = Inner()

    obj = Outer()
    _set_nested_attr(obj, "a.b", 99)
    assert obj.a.b == 99

    # setattr creates the attribute if it doesn't exist, so this does not raise an error.
    # The primary goal is ensuring it sets existing nested attributes correctly.
    _set_nested_attr(obj.a, "c", 101)
    assert obj.a.c == 101
