"""
Integration tests for the Orchestrator.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Iterator, Tuple, List, Any, Dict

from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Signal, ValidationScores, Trade
from praxis_engine.services.config_service import load_config

def mock_pre_calculate(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """A helper to mock the pre-calculation by adding required columns."""
    df["hist_win_rate"] = 0.0
    df["hist_profit_factor"] = 0.0
    df["hist_sample_size"] = 0
    df[f"hurst_{config.strategy_params.hurst_length}"] = 0.4
    df["adf_p_value"] = 0.04
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

[market_data]
index_ticker = "^NSEI"
vix_ticker = "^INDIAVIX"
training_start_date = "2010-01-01"
cache_dir = "test_cache/market"

[regime_model]
model_path = "results/regime_model.joblib"
volatility_threshold_percentile = 0.75

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
reward_risk_ratio = 1.75

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
    config = load_config(str(config_file))
    return config

@pytest.fixture
def mock_orchestrator(test_config: Config) -> Iterator[Tuple[Orchestrator, MagicMock, MagicMock, MagicMock, MagicMock]]:
    """A fixture to create an Orchestrator with mocked services."""
    with patch('praxis_engine.core.orchestrator.DataService') as MockDataService, \
         patch('praxis_engine.core.orchestrator.SignalEngine') as MockSignalEngine, \
         patch('praxis_engine.core.orchestrator.ValidationService') as MockValidationService, \
         patch('praxis_engine.core.orchestrator.ExecutionSimulator') as MockExecutionSimulator:

        mock_data_service = MockDataService.return_value
        mock_signal_engine = MockSignalEngine.return_value
        mock_validation_service = MockValidationService.return_value
        mock_execution_simulator = MockExecutionSimulator.return_value

        orchestrator = Orchestrator(test_config)

        yield orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_execution_simulator

@pytest.fixture
def sample_trade_kwargs() -> Dict[str, Any]:
    """Provides a sample of the extra data needed to create a Trade object."""
    return {
        "exit_reason": "PROFIT_TARGET",
        "liquidity_score": 0.8,
        "regime_score": 0.7,
        "stat_score": 0.9,
        "composite_score": 0.504,
        "entry_hurst": 0.4,
        "entry_adf_p_value": 0.04,
        "entry_sector_vol": 0.15,
        "config_bb_length": 20,
        "config_rsi_length": 14,
        "config_atr_multiplier": 2.0,
    }

def test_run_backtest_atr_exit_triggered(mock_orchestrator: Tuple[Orchestrator, ...], sample_trade_kwargs: Dict) -> None:
    """
    Tests that a trade is exited correctly when the ATR stop-loss is triggered.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    data = {
        "Open": [100.0] * 30, "High": [101.0] * 30, "Low": [99.0] * 30,
        "Close": [100.0] * 30, "Volume": [1000.0] * 30,
    }
    df = pd.DataFrame(data, index=dates)
    mock_data_service.get_data.return_value = df

    signals = [
        Signal(entry_price=100, stop_loss=96, exit_target_days=10, frames_aligned=[], sector_vol=0.1)
    ] + ([None] * 20)
    mock_signal_engine.generate_signal.side_effect = signals
    mock_validation_service.validate.return_value = ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9)

    with patch.object(orchestrator, '_determine_exit', return_value=(dates[17], 96.0, "ATR_STOP_LOSS")) as mock_determine_exit, \
         patch('praxis_engine.core.orchestrator.precompute_indicators', side_effect=lambda df, config: df), \
         patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=lambda df: df):

        orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    mock_determine_exit.assert_called_once()
    mock_execution_simulator.simulate_trade.assert_called_once()
    call_args = mock_execution_simulator.simulate_trade.call_args[1]

    assert call_args['exit_date'] == dates[17]
    assert call_args['exit_reason'] == "ATR_STOP_LOSS"

def test_run_backtest_metrics_tracking(mock_orchestrator: Tuple[Orchestrator, ...]) -> None:
    """
    Tests that the BacktestMetrics are tracked correctly through the funnel.
    """
    orchestrator, mock_data_service, mock_signal_engine, mock_validation_service, mock_execution_simulator = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30, "High": [105.0]*30, "Low": [95.0]*30, "Open": [100.0]*30, "sector_vol": [15.0]*30}, index=dates)
    mock_data_service.get_data.return_value = df

    mock_signal_engine.generate_signal.side_effect = [
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1),
        Signal(entry_price=100, stop_loss=90, exit_target_days=10, frames_aligned=[], sector_vol=0.1),
        *([None] * 28)
    ]
    mock_validation_service.validate.side_effect = [
        ValidationScores(liquidity_score=0.4, regime_score=0.9, stat_score=0.8),
        ValidationScores(liquidity_score=0.9, regime_score=0.9, stat_score=0.9),
    ]

    with patch('praxis_engine.core.orchestrator.precompute_indicators', side_effect=lambda df, config: df), \
         patch.object(orchestrator, '_pre_calculate_historical_performance', side_effect=lambda df: df):
        result = orchestrator.run_backtest("TEST.NS", "2023-01-01", "2023-01-30")

    metrics = result["metrics"]
    assert metrics.potential_signals == 2
    assert metrics.rejections_by_guard.get("LiquidityGuard") == 1
    assert metrics.trades_executed == 1
    mock_execution_simulator.simulate_trade.assert_called_once()

def test_determine_exit_reasons(mock_orchestrator: Tuple[Orchestrator, ...], test_config: Config) -> None:
    """
    Tests that _determine_exit returns the correct reason string for each exit type.
    """
    orchestrator, _, _, _, _ = mock_orchestrator

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=30))
    df = pd.DataFrame({
        "High": [105.0] * 30, "Low": [95.0] * 30, "Open": [100.0] * 30,
        "Close": [100.0] * 30, "ATR_14": [4.0] * 30
    }, index=dates)

    # Scenario 1: ATR Stop Loss
    df_atr = df.copy()
    df_atr.loc[dates[5], "Low"] = 91.9 # stop_loss is 100 - (4*2) = 92
    _, _, reason_atr = orchestrator._determine_exit(1, 100.0, df_atr, df_atr.iloc[:1])
    assert reason_atr == "ATR_STOP_LOSS"

    # Scenario 2: Profit Target
    df_profit = df.copy()
    df_profit.loc[dates[6], "High"] = 114.1 # profit_target is 100 + (8 * 1.75) = 114
    _, _, reason_profit = orchestrator._determine_exit(1, 100.0, df_profit, df_profit.iloc[:1])
    assert reason_profit == "PROFIT_TARGET"

    # Scenario 3: Max Hold Timeout
    _, _, reason_timeout = orchestrator._determine_exit(1, 100.0, df, df.iloc[:1])
    assert reason_timeout == "MAX_HOLD_TIMEOUT"
