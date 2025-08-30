import pandas as pd
import pytest
from typing import List, Dict

from praxis_engine.core.models import BacktestMetrics, BacktestSummary, Trade, Signal, RunMetadata
from praxis_engine.services.report_generator import ReportGenerator

@pytest.fixture
def sample_metrics() -> BacktestMetrics:
    """Provides a sample BacktestMetrics object for testing."""
    return BacktestMetrics(
        potential_signals=100,
        rejections_by_guard={"LiquidityGuard": 20, "StatGuard": 30},
        rejections_by_llm=10,
        trades_executed=40,
    )

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


def test_generate_backtest_report_no_trades(sample_metrics: BacktestMetrics) -> None:
    """
    Tests that the report generator handles the case with no trades.
    """
    report_generator = ReportGenerator()
    report = report_generator.generate_backtest_report([], sample_metrics, "2023-01-01", "2023-12-31")
    assert "No trades were executed" in report


def test_generate_backtest_report_with_metadata(sample_trades: List[Trade], sample_metrics: BacktestMetrics) -> None:
    """
    Tests that the report generator correctly renders the metadata section.
    """
    report_generator = ReportGenerator()
    metadata = RunMetadata(
        run_timestamp="2025-08-30 12:00:00 UTC",
        config_path="config.ini",
        git_commit_hash="abcdef1",
    )
    report = report_generator.generate_backtest_report(
        sample_trades, sample_metrics, "2023-01-01", "2023-12-31", metadata=metadata
    )

    assert "Run Configuration & Metadata" in report
    assert "| Run Timestamp | 2025-08-30 12:00:00 UTC |" in report
    assert "| Config File | `config.ini` |" in report
    assert "| Git Commit Hash | `abcdef1` |" in report


def test_generate_filtering_funnel_table(sample_metrics: BacktestMetrics) -> None:
    """Tests the generation of the filtering funnel table."""
    report_generator = ReportGenerator()
    table = report_generator._generate_filtering_funnel_table(sample_metrics)

    assert "Filtering Funnel" in table
    assert "| Potential Signals | 100 | 100.00% |" in table
    assert "| Survived Guardrails | 50 | 50.00% |" in table
    assert "| Survived LLM Audit | 40 | 80.00% |" in table
    assert "| Trades Executed | 40 | 100.00% |" in table


def test_generate_rejection_analysis_table(sample_metrics: BacktestMetrics) -> None:
    """Tests the generation of the rejection analysis table."""
    report_generator = ReportGenerator()
    table = report_generator._generate_rejection_analysis_table(sample_metrics.rejections_by_guard)

    assert "Guardrail Rejection Analysis" in table
    # Note: The output uses escaped newlines for the multiline string
    assert "| StatGuard | 30 | 60.00% |" in table.replace("\\n", "\n")
    assert "| LiquidityGuard | 20 | 40.00% |" in table.replace("\\n", "\n")


def test_calculate_kpis_with_sample_data(sample_trades: List[Trade]) -> None:
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


def test_generate_sensitivity_report() -> None:
    """
    Tests the sensitivity report generation.
    """
    results = [
        BacktestSummary(parameter_value=20.0, total_trades=10, win_rate_pct=50.0, profit_factor=2.5, net_return_pct_mean=1.5, net_return_pct_std=0.5),
        BacktestSummary(parameter_value=22.0, total_trades=12, win_rate_pct=60.0, profit_factor=3.0, net_return_pct_mean=2.0, net_return_pct_std=0.6),
    ]
    parameter_name = "filters.sector_vol_threshold"

    report_generator = ReportGenerator()
    report = report_generator.generate_sensitivity_report(results, parameter_name)

    assert f"Sensitivity Analysis Report for '{parameter_name}'" in report
    assert "| filters.sector_vol_threshold | Total Trades | Win Rate (%) | Profit Factor | Avg Net Return (%) | Std Dev Return (%) |" in report
    assert "| 20.0000 | 10 | 50.00 | 2.50 | 1.50 | 0.50 |" in report
    assert "| 22.0000 | 12 | 60.00 | 3.00 | 2.00 | 0.60 |" in report
