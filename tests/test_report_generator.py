import pandas as pd
import pytest
from typing import List

from praxis_engine.core.models import Trade, Signal
from praxis_engine.services.report_generator import ReportGenerator

@pytest.fixture
def sample_trades() -> List[Trade]:
    """
    Provides a sample list of Trade objects for testing.
    """
    # Create a dummy signal to be used in trades
    dummy_signal = Signal(
        entry_price=100.0,
        stop_loss=95.0,
        exit_target_days=20,
        frames_aligned=["daily"],
        sector_vol=0.15,
    )
    trades = [
        Trade(
            stock="RELIANCE.NS",
            entry_date=pd.Timestamp("2023-01-02"),
            exit_date=pd.Timestamp("2023-01-22"),
            entry_price=100.0,
            exit_price=110.0,
            net_return_pct=0.10,
            confidence_score=0.8,
            signal=dummy_signal,
        ),
        Trade(
            stock="RELIANCE.NS",
            entry_date=pd.Timestamp("2023-02-01"),
            exit_date=pd.Timestamp("2023-02-21"),
            entry_price=110.0,
            exit_price=105.0,
            net_return_pct=-0.045,
            confidence_score=0.75,
            signal=dummy_signal,
        ),
        Trade(
            stock="TCS.NS",
            entry_date=pd.Timestamp("2023-03-01"),
            exit_date=pd.Timestamp("2023-03-21"),
            entry_price=200.0,
            exit_price=220.0,
            net_return_pct=0.10,
            confidence_score=0.9,
            signal=dummy_signal,
        ),
    ]
    return trades


def test_generate_backtest_report_no_trades():
    """
    Tests that the report generator handles the case with no trades.
    """
    report_generator = ReportGenerator()
    report = report_generator.generate_backtest_report([], "2023-01-01", "2023-12-31")
    assert "No trades were executed" in report


def test_calculate_kpis_with_sample_data(sample_trades):
    """
    Tests the KPI calculations with a sample set of trades.
    """
    report_generator = ReportGenerator()
    start_date = "2023-01-01"
    end_date = "2023-03-31"
    kpis = report_generator._calculate_kpis(sample_trades, start_date, end_date)

    # Expected values based on manual calculation
    expected_win_rate = 2 / 3
    expected_profit_factor = (0.10 + 0.10) / 0.045

    # Manual equity curve calculation
    # End of Day 1: 1.10
    # End of Day 2: 1.10 * (1 - 0.045) = 1.0505
    # End of Day 3: 1.0505 * 1.10 = 1.15555
    # Drawdown is from 1.10 to 1.0505. (1.0505 - 1.10) / 1.10 = -0.045
    expected_max_drawdown = -0.045

    assert kpis["win_rate"] == pytest.approx(expected_win_rate)
    assert kpis["profit_factor"] == pytest.approx(expected_profit_factor)
    assert kpis["max_drawdown"] == pytest.approx(expected_max_drawdown, abs=1e-3)

    # Check for plausible values for annualized return and sharpe
    # These are highly dependent on the daily return series construction
    assert kpis["net_annualized_return"] > 0
    assert kpis["sharpe_ratio"] > 0
