"""
Integration tests for the Orchestrator.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Iterator, Tuple

from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Signal, ValidationScores
from praxis_engine.services.config_service import ConfigService

@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """A fixture to create a default Config object for testing."""
    config_content = """
[data]
cache_dir = "test_cache"
stocks_to_backtest = ["TEST.NS"]
start_date = "2022-01-01"
end_date = "2023-01-01"
sector_map = {"TEST.NS": "^TESTINDEX"}

[strategy_params]
bb_length = 20
bb_std = 2.0
rsi_length = 14
hurst_length = 100
exit_days = 20
min_history_days = 15
liquidity_lookback_days = 5

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[scoring]
liquidity_score_min_turnover_crores = 1.0
liquidity_score_max_turnover_crores = 4.0
regime_score_min_volatility_pct = 30.0
regime_score_max_volatility_pct = 15.0
hurst_score_min_h = 0.5
hurst_score_max_h = 0.4
adf_score_min_pvalue = 0.1
adf_score_max_pvalue = 0.01

[llm]
provider = "test"
confidence_threshold = 0.6
min_composite_score_for_llm = 0.5
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = false
require_monthly_not_oversold = true
rsi_threshold = 30

[exit_logic]
use_atr_exit = true
atr_period = 14
atr_stop_loss_multiplier = 2.0
max_holding_days = 10

[cost_model]
brokerage_rate = 0.0
brokerage_max = 0.0
stt_rate = 0.0
assumed_trade_value_inr = 100000
slippage_volume_threshold = 1000000
slippage_rate_high_liquidity = 0.0
slippage_rate_low_liquidity = 0.0
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)
    # Add scoring config to the main config object
    config = ConfigService(str(config_file)).load_config()
    return config

@pytest.fixture
def mock_orchestrator(test_config: Config) -> Iterator[Tuple[MagicMock, ...]]:
    """A fixture to create an Orchestrator with mocked services."""
    with patch('praxis_engine.core.orchestrator.DataService') as MockDataService, \
         patch('praxis_engine.core.orchestrator.SignalEngine') as MockSignalEngine, \
         patch('praxis_engine.core.orchestrator.ValidationService') as MockValidationService, \
         patch('praxis_engine.core.orchestrator.LLMAuditService') as MockLLMAuditService, \
         patch('praxis_engine.core.orchestrator.ExecutionSimulator') as MockExecutionSimulator:

        mock_data_service = MockDataService.return_value
        mock_signal_engine = MockSignalEngine.return_value
        mock_validation_service = MockValidationService.return_value
        mock_llm_audit_service = MockLLMAuditService.return_value
        mock_execution_simulator = MockExecutionSimulator.return_value

        orchestrator = Orchestrator(test_config)

        yield orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator

def test_run_backtest_atr_exit_triggered(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that a trade is exited correctly when the ATR stop-loss is triggered.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "High":  [105.0] * 30, "Low":   [95.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30, "sector_vol": [15.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    df.loc[dates[17], "Low"] = 79.9
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1, strength_score=0.5)
    ] + ([None] * 15)
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)
    mock_llm_audit_service.get_confidence_score.return_value = 0.9

    orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['entry_date'] == dates[15]
    assert call_args['exit_date'] == dates[17]
    assert call_args['exit_price'] == 80.0


def test_run_backtest_low_score_skips_llm(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that the LLM audit is skipped if the composite score is below the threshold.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30, "High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "sector_vol": [15.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.return_value = Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1, strength_score=0.5)
    # This composite score (0.5*0.5*0.5=0.125) is below the 0.5 threshold in config
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.5, regime_score=0.5, stat_score=0.5)

    orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    # Assert that the LLM service was never called
    mock_llm_audit_service.get_confidence_score.assert_not_called()
    # Assert that no trade was executed
    mock_execution_simulator.simulate_trade.assert_not_called()


def test_run_backtest_metrics_tracking(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that the BacktestMetrics are tracked correctly through the funnel.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30, "High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "sector_vol": [15.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    # Simulate a sequence of events
    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1, strength_score=0.5), # 1. Rejected by guard
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1, strength_score=0.5), # 2. Rejected by LLM
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1, strength_score=0.5), # 3. Executed
        *([None] * 27) # No more signals
    ]
    mock_validation_service.validate.side_effect = [
        ValidationScores(liquidity_score=0.4, regime_score=0.9, stat_score=0.8), # Rejected (liquidity is lowest)
        ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9), # Passes
        ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9), # Passes
    ]
    mock_llm_audit_service.get_confidence_score.side_effect = [
        0.4, # Rejected
        0.9, # Passes
    ]
    mock_llm_audit_service.get_confidence_score.return_value = 0.9

    result = orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")
    metrics = result["metrics"]

    assert metrics.potential_signals == 3
    assert metrics.rejections_by_guard.get("LiquidityGuard") == 1
    assert metrics.rejections_by_llm == 1
    assert metrics.trades_executed == 1
    mock_execution_simulator.simulate_trade.assert_called_once()
