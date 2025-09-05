"""
Integration tests for the Orchestrator.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Iterator, Tuple, List, Any

from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Signal, ValidationScores, Trade
from praxis_engine.services.config_service import ConfigService

def mock_pre_calculate(df: pd.DataFrame) -> pd.DataFrame:
    """A helper to mock the pre-calculation by adding required columns."""
    df["hist_win_rate"] = 0.0
    df["hist_profit_factor"] = 0.0
    df["hist_sample_size"] = 0
    return df

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
use_llm_audit = true
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
use_symmetrical_bb_exit = true

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
def mock_orchestrator(test_config: Config) -> Iterator[Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]]:
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

def test_run_backtest_atr_exit_triggered(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests that a trade is exited correctly when the ATR stop-loss is triggered.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    # Make price action have low volatility so ATR is small
    data = {
        "High":  [101.0] * 30, "Low":   [99.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30, "sector_vol": [15.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    # ATR will be ~2. Stop loss price will be ~ 100 - (2 * 2.0) = 96.
    df.loc[dates[17], "Low"] = 95.9
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=96, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 20)
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)
    mock_llm_audit_service.get_confidence_score.return_value = 0.9

    with patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=mock_pre_calculate):
        orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['entry_date'] == dates[15]
    assert call_args['exit_date'] == dates[17]
    assert pytest.approx(call_args['exit_price']) == 96.0


def test_run_backtest_low_score_skips_llm(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests that the LLM audit is skipped if the composite score is below the threshold.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30, "High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "sector_vol": [15.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.return_value = Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    # This composite score (0.5*0.5*0.5=0.125) is below the 0.5 threshold in config
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.5, regime_score=0.5, stat_score=0.5)

    with patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=mock_pre_calculate):
        orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    # Assert that the LLM service was never called
    mock_llm_audit_service.get_confidence_score.assert_not_called()
    # Assert that no trade was executed
    mock_execution_simulator.simulate_trade.assert_not_called()


def test_run_backtest_metrics_tracking(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests that the BacktestMetrics are tracked correctly through the funnel.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30, "High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "sector_vol": [15.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    # Simulate a sequence of events
    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1), # 1. Rejected by guard
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1), # 2. Rejected by LLM
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1), # 3. Executed
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

    with patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=mock_pre_calculate):
        result = orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    metrics = result["metrics"]

    assert metrics.potential_signals == 3
    assert metrics.rejections_by_guard.get("LiquidityGuard") == 1
    assert metrics.rejections_by_llm == 1
    assert metrics.trades_executed == 1
    mock_execution_simulator.simulate_trade.assert_called_once()

def test_pre_calculate_historical_performance(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests the _pre_calculate_historical_performance method for point-in-time correctness.
    """
    orchestrator, _, mock_signal_engine, mock_validation_service, _, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=40))
    data = {
        "High": [105.0] * 40, "Low": [95.0] * 40, "Open": [100.0] * 40,
        "Close": [100.0] * 40, "Volume": [1000.0] * 40, "sector_vol": [15.0] * 40,
        "ATR_14": [10.0] * 40,
    }
    df = pd.DataFrame(data, index=dates)

    # Signal at index 20 -> Enters at 21. _determine_exit will calculate exit at 31 (max hold).
    # We mock simulate_trade to return a trade that exits earlier, on the 26th.
    # Signal at index 30 -> Enters at 31. _determine_exit will calculate exit at 33 (ATR stop).
    df.loc[dates[33], "Low"] = 79.0

    # Signal is checked for i from 15 to 38.
    # Signal at i=20 is the 6th call (index 5).
    # Signal at i=30 is 10 calls later (index 15).
    side_effect_list: List[Any] = [None] * 24
    side_effect_list[5] = Signal(entry_price=100, stop_loss=90, exit_target_days=5, frames_aligned=[], sector_vol=0.1)
    side_effect_list[15] = Signal(entry_price=100, stop_loss=90, exit_target_days=5, frames_aligned=[], sector_vol=0.1)
    mock_signal_engine.generate_signal.side_effect = side_effect_list

    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)

    signal_obj = Signal(entry_price=100, stop_loss=90, exit_target_days=5, frames_aligned=[], sector_vol=0.1)
    trade1 = Trade(stock='TEST.NS', entry_date=dates[21], exit_date=dates[26], entry_price=100, exit_price=110, net_return_pct=0.1, signal=signal_obj, confidence_score=1.0)
    trade2 = Trade(stock='TEST.NS', entry_date=dates[31], exit_date=dates[33], entry_price=100, exit_price=90, net_return_pct=-0.1, signal=signal_obj, confidence_score=1.0)
    mock_execution_simulator.simulate_trade.side_effect = [trade1, trade2]

    with patch.object(orchestrator, '_determine_exit', side_effect=[(dates[26], 110.0), (dates[33], 90.0)]) as mock_determine_exit:
        result_df = orchestrator._pre_calculate_historical_performance(df)
        assert mock_determine_exit.call_count == 2

    # Before any trades exit, stats are 0
    assert result_df.loc[dates[25], "hist_win_rate"] == 0
    assert result_df.loc[dates[25], "hist_sample_size"] == 0

    # On the day the first trade exits
    assert result_df.loc[dates[26], "hist_win_rate"] == 100.0
    assert result_df.loc[dates[26], "hist_profit_factor"] == 999.0
    assert result_df.loc[dates[26], "hist_sample_size"] == 1

    # Before the second trade exits
    assert result_df.loc[dates[32], "hist_win_rate"] == 100.0
    assert result_df.loc[dates[32], "hist_sample_size"] == 1

    # On the day the second trade exits
    assert result_df.loc[dates[33], "hist_win_rate"] == 50.0
    assert result_df.loc[dates[33], "hist_profit_factor"] == 1.0
    assert result_df.loc[dates[33], "hist_sample_size"] == 2


def test_run_backtest_symmetrical_bb_exit_triggered(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests that a trade is exited correctly when the symmetrical profit target (upper BB) is hit.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "High":  [105.0] * 30, "Low":   [95.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30, "sector_vol": [15.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    # The price hits the profit target on this day. Upper BB is mocked to be 108.0
    df.loc[dates[18], "High"] = 108.1
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 20)
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)
    mock_llm_audit_service.get_confidence_score.return_value = 0.9

    # We need to mock the precompute function to control the indicator values
    with patch('praxis_engine.core.orchestrator.precompute_indicators') as mock_precompute:
        def precompute_side_effect(df, config):
            df_copy = df.copy()
            df_copy[f"BBU_{config.strategy_params.bb_length}_{config.strategy_params.bb_std}"] = 108.0
            df_copy[f"ATR_{config.exit_logic.atr_period}"] = 5.0 # Low ATR so stop loss is not hit
            return df_copy
        mock_precompute.side_effect = precompute_side_effect

        with patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=mock_pre_calculate):
            orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['entry_date'] == dates[15]
    assert call_args['exit_date'] == dates[18]
    assert pytest.approx(call_args['exit_price']) == 108.0


def test_run_backtest_atr_takes_precedence_over_symmetrical_bb(mock_orchestrator: Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], test_config: Config) -> None:
    """
    Tests that the ATR stop-loss triggers even if the BB profit target is also met on the same day.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_llm_audit_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "High":  [105.0] * 30, "Low":   [95.0] * 30, "Open":  [100.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30, "sector_vol": [15.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    # On this day, the high hits the profit target, but the low also hits the stop loss.
    df.loc[dates[17], "High"] = 110.1
    df.loc[dates[17], "Low"] = 79.9 # Stop loss is at 80.0
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=80, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 20)
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)
    mock_llm_audit_service.get_confidence_score.return_value = 0.9

    with patch('praxis_engine.core.orchestrator.precompute_indicators') as mock_precompute:
        def precompute_side_effect(df, config):
            df_copy = df.copy()
            # The BBU is set to a value that is hit on the same day as the stop loss
            df_copy[f"BBU_{config.strategy_params.bb_length}_{config.strategy_params.bb_std}"] = 110.0
            # ATR is 10, stop multiplier is 2.0. Entry is 100. Stop loss is 100 - (10 * 2) = 80.0
            df_copy[f"ATR_{config.exit_logic.atr_period}"] = 10.0
            return df_copy
        mock_precompute.side_effect = precompute_side_effect

        with patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=mock_pre_calculate):
            orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    # The exit must be the stop loss price because it's checked first.
    assert call_args['exit_date'] == dates[17]
    assert call_args['exit_price'] == 80.0
