"""
Unit tests for the ReportGenerator service.
"""
import pandas as pd
import numpy as np
import pytest

from core.models import StrategyDefinition, Indicator, PerformanceReport
from services.report_generator import ReportGenerator


@pytest.fixture
def mock_strategy_def() -> StrategyDefinition:
    """Provides a sample StrategyDefinition for tests."""
    return StrategyDefinition(
        strategy_name="Test_Strategy",
        indicators=[
            Indicator(name="sma1", function="sma", params={"length": 50})
        ],
        buy_condition="sma1 > 0",
        sell_condition="sma1 < 0",
    )


@pytest.fixture
def mock_stats_series() -> pd.Series:
    """Provides a sample backtest statistics Series."""
    return pd.Series({
        "Sharpe Ratio": 1.5,
        "Sortino Ratio": 2.5,
        "Max. Drawdown [%]": -15.5,
        "Return (Ann.) [%]": 25.0,
        "Equity Final [$]": 125000,
        "# Trades": 4,
    })


@pytest.fixture
def mock_trades_df() -> pd.DataFrame:
    """Provides a sample trades DataFrame with mixed results."""
    data = {
        "Size": [10, -10, 5, -5],
        "EntryBar": [10, 20, 30, 40],
        "ExitBar": [15, 25, 35, 45],
        "EntryPrice": [100, 110, 105, 115],
        "ExitPrice": [105, 105, 110, 110],
        "PnL": [50, 50, 25, 25],
        "ReturnPct": [0.05, 0.045, 0.047, -0.043], # 3 wins, 1 loss
        "Duration": [5, 5, 5, 5],
    }
    return pd.DataFrame(data)


def test_generate_report_happy_path(
    mock_strategy_def, mock_stats_series, mock_trades_df
):
    """
    Tests that a report is generated correctly for a typical backtest result.
    """
    report = ReportGenerator.generate(mock_stats_series, mock_trades_df, mock_strategy_def)

    assert isinstance(report, PerformanceReport)
    assert report.strategy == mock_strategy_def
    assert report.sharpe_ratio == 1.5
    assert report.sortino_ratio == 2.5
    assert report.max_drawdown_pct == -15.5
    assert report.annual_return_pct == 25.0

    summary = report.trade_summary
    assert summary.total_trades == 4
    assert summary.win_rate_pct == pytest.approx(75.0)

    # profit = 0.05 + 0.045 + 0.047 = 0.142
    # loss = 0.043
    # profit_factor = 0.142 / 0.043 = 3.302
    assert summary.profit_factor == pytest.approx(3.302, abs=1e-3)

    assert summary.avg_win_pct == pytest.approx(((0.05 + 0.045 + 0.047) / 3) * 100)
    assert summary.avg_loss_pct == pytest.approx(-0.043 * 100)
    assert summary.max_consecutive_losses == 1
    assert summary.avg_trade_duration_bars == 5


def test_generate_report_no_trades(mock_strategy_def, mock_stats_series):
    """
    Tests report generation when the backtest produces no trades.
    """
    empty_trades = pd.DataFrame()
    report = ReportGenerator.generate(mock_stats_series, empty_trades, mock_strategy_def)

    assert isinstance(report, PerformanceReport)
    summary = report.trade_summary
    assert summary.total_trades == 0
    assert summary.win_rate_pct == 0.0
    assert summary.profit_factor == 0.0
    assert summary.max_consecutive_losses == 0


def test_generate_report_no_losses(mock_strategy_def, mock_stats_series):
    """
    Tests report generation when there are no losing trades.
    """
    all_wins_data = {
        "ReturnPct": [0.05, 0.045, 0.047, 0.02],
        "Duration": [5, 5, 5, 5],
    }
    all_wins_df = pd.DataFrame(all_wins_data)
    report = ReportGenerator.generate(mock_stats_series, all_wins_df, mock_strategy_def)

    summary = report.trade_summary
    assert summary.win_rate_pct == 100.0
    assert summary.profit_factor == np.inf
    assert np.isnan(summary.avg_loss_pct) # mean of empty series is NaN
    assert summary.max_consecutive_losses == 0

def test_generate_report_no_wins(mock_strategy_def, mock_stats_series):
    """
    Tests report generation when there are no winning trades.
    """
    all_losses_data = {
        "ReturnPct": [-0.05, -0.045, -0.047, -0.02],
        "Duration": [5, 5, 5, 5],
    }
    all_losses_df = pd.DataFrame(all_losses_data)
    report = ReportGenerator.generate(mock_stats_series, all_losses_df, mock_strategy_def)

    summary = report.trade_summary
    assert summary.win_rate_pct == 0.0
    assert summary.profit_factor == 0.0
    assert np.isnan(summary.avg_win_pct) # mean of empty series is NaN
    assert summary.max_consecutive_losses == 4
