"""
Integration tests for the Orchestrator.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Iterator, Tuple

from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Signal, ValidationResult
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

[llm]
provider = "test"
confidence_threshold = 0.6
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
    return ConfigService(str(config_file)).load_config()

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
        orchestrator.data_service = mock_data_service
        orchestrator.signal_engine = mock_signal_engine
        orchestrator.validation_service = mock_validation_service
        orchestrator.llm_audit_service = mock_llm_audit_service
        orchestrator.execution_simulator = mock_execution_simulator

        yield orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator

def test_run_backtest_atr_exit_triggered(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that a trade is exited correctly when the ATR stop-loss is triggered.
    """
    orchestrator, mock_data_service, mock_signal_engine, _, _, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "High":  [105.0] * 30, "Low":   [95.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    # ATR of a constant H-L of 10 is 10. Stop multiplier is 2. Stop price = 100 - (10 * 2) = 80.
    # Set the trigger price on day index 17, after the signal on index 15
    df.loc[dates[17], "Low"] = 79.9
    mock_data_service.get_data.return_value = df

    # Signal is generated on the first possible day (i=15)
    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 15)
    orchestrator.validation_service.validate.return_value = ValidationResult(is_valid=True)
    orchestrator.llm_audit_service.get_confidence_score.return_value = 0.9

    orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['entry_date'] == dates[15]
    assert call_args['exit_date'] == dates[17]
    assert call_args['exit_price'] == 80.0


def test_run_backtest_atr_exit_timeout(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that a trade is exited correctly on timeout when the ATR stop is not hit.
    """
    orchestrator, mock_data_service, mock_signal_engine, _, _, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "High":  [105.0] * 30, "Low":   [95.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 15)
    orchestrator.validation_service.validate.return_value = ValidationResult(is_valid=True)
    orchestrator.llm_audit_service.get_confidence_score.return_value = 0.9

    orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['entry_date'] == dates[15]
    max_hold = test_config.exit_logic.max_holding_days
    expected_exit_date = dates[15 + max_hold]
    assert call_args['exit_date'] == expected_exit_date
    assert call_args['exit_price'] == 100


def test_run_backtest_legacy_exit(mock_orchestrator: Tuple[MagicMock, ...], test_config: Config) -> None:
    """
    Tests that the legacy fixed-day exit logic is used when use_atr_exit is False.
    """
    test_config.exit_logic.use_atr_exit = False
    orchestrator, mock_data_service, mock_signal_engine, _, _, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "Close": [100.0]*30, "Volume": [1000.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    exit_target_days = test_config.strategy_params.exit_days
    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=exit_target_days, frames_aligned=[], sector_vol=0.1),
    ] + ([None] * 25)
    orchestrator.validation_service.validate.return_value = ValidationResult(is_valid=True)
    orchestrator.llm_audit_service.get_confidence_score.return_value = 0.9

    orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    # FIX: The entry index is now 15, not 5
    entry_index = 15
    timeout_index = entry_index + exit_target_days
    expected_exit_date = dates[min(timeout_index, len(df) - 1)]
    assert call_args['exit_date'] == expected_exit_date
