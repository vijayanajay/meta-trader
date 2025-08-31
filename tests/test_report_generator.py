import pandas as pd
import pytest
from typing import List, Dict

from praxis_engine.core.models import BacktestMetrics, BacktestSummary, Trade, Signal, RunMetadata, BacktestMetrics
from praxis_engine.services.report_generator import ReportGenerator

@pytest.fixture
def report_generator() -> ReportGenerator:
    """Provides a ReportGenerator instance for testing."""
    return ReportGenerator()

@pytest.fixture
def sample_metrics() -> BacktestMetrics:
    """Provides a sample BacktestMetrics object for testing."""
    return BacktestMetrics(
        potential_signals=10,
        rejections_by_guard={"LiquidityGuard": 2, "StatGuard": 1},
        rejections_by_llm=1,
        trades_executed=2,
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
        strength_score=0.5,
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
            net_return_pct=0.05,
            confidence_score=0.75,
            signal=dummy_signal,
        ),
    ]
    return trades


def test_generate_backtest_report_no_trades(report_generator: ReportGenerator, sample_metrics: BacktestMetrics) -> None:
    """
    Tests that the report generator handles the case with no trades.
    """
    report = report_generator.generate_backtest_report([], sample_metrics, "2023-01-01", "2023-12-31")
    assert "No trades were executed" in report


def test_generate_backtest_report_with_metadata(report_generator: ReportGenerator, sample_trades: List[Trade], sample_metrics: BacktestMetrics) -> None:
    """
    Tests that the report generator correctly renders the metadata section.
    """
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
    assert "### Trade Distribution Analysis" in report
    assert "### Net Return (%) Distribution" in report


def test_generate_filtering_funnel_table(report_generator: ReportGenerator, sample_metrics: BacktestMetrics) -> None:
    """Tests the generation of the filtering funnel table."""
    table = report_generator._generate_filtering_funnel_table(sample_metrics)

    assert "Filtering Funnel" in table
    assert "| Potential Signals | 10 | 100.00% |" in table
    assert "| Survived Guardrails | 7 | 70.00% |" in table
    assert "| Survived LLM Audit | 6 | 85.71% |" in table
    assert "| Trades Executed | 2 | 33.33% |" in table


def test_generate_rejection_analysis_table(report_generator: ReportGenerator, sample_metrics: BacktestMetrics) -> None:
    """Tests the generation of the rejection analysis table."""
    table = report_generator._generate_rejection_analysis_table(sample_metrics.rejections_by_guard)

    assert "Guardrail Rejection Analysis" in table
    # Note: The output uses escaped newlines for the multiline string
    assert "| LiquidityGuard | 2 | 66.67% |" in table.replace("\\n", "\n")
    assert "| StatGuard | 1 | 33.33% |" in table.replace("\\n", "\n")


def test_calculate_kpis_with_sample_data(report_generator: ReportGenerator, sample_trades: List[Trade]) -> None:
    """
    Tests the KPI calculations with a sample set of trades.
    """
    start_date = "2023-01-01"
    end_date = "2023-03-31"
    kpis = report_generator._calculate_kpis(sample_trades, start_date, end_date)

    assert kpis["win_rate"] == pytest.approx(1.0)
    assert kpis["profit_factor"] == pytest.approx(float('inf'))
    assert kpis["avg_holding_period_days"] == pytest.approx(20.0)
    assert kpis["avg_win_pct"] == pytest.approx(0.075)
    assert kpis["best_trade_pct"] == pytest.approx(0.10)
    assert kpis["worst_trade_pct"] == pytest.approx(0.05)


def test_generate_sensitivity_report(report_generator: ReportGenerator) -> None:
    """
    Tests the sensitivity report generation.
    """
    results = [
        BacktestSummary(parameter_value=20.0, total_trades=10, win_rate_pct=50.0, profit_factor=2.5, net_return_pct_mean=1.5, net_return_pct_std=0.5),
        BacktestSummary(parameter_value=22.0, total_trades=12, win_rate_pct=60.0, profit_factor=3.0, net_return_pct_mean=2.0, net_return_pct_std=0.6),
    ]
    parameter_name = "filters.sector_vol_threshold"

    report = report_generator.generate_sensitivity_report(results, parameter_name)

    assert f"Sensitivity Analysis Report for '{parameter_name}'" in report
    assert "| filters.sector_vol_threshold | Total Trades | Win Rate (%) | Profit Factor | Avg Net Return (%) | Std Dev Return (%) |" in report
    assert "| 20.0000 | 10 | 50.00 | 2.50 | 1.50 | 0.50 |" in report
    assert "| 22.0000 | 12 | 60.00 | 3.00 | 2.00 | 0.60 |" in report

def test_generate_per_stock_report(report_generator: ReportGenerator, sample_trades: List[Trade], sample_metrics: BacktestMetrics) -> None:
    """
    Tests the generation of the per-stock report.
    """
    per_stock_metrics = {"STOCKA": sample_metrics, "STOCKB": BacktestMetrics()}
    per_stock_trades = {"STOCKA": sample_trades, "STOCKB": []}

    report = report_generator.generate_per_stock_report(
        per_stock_metrics, per_stock_trades
    )

    assert "### Per-Stock Performance Breakdown" in report
    assert "| STOCKA | 0.15% | 2 | 10 | 3 | 1 |" in report
    assert "| STOCKB | 0.00% | 0 | 0 | 0 | 0 |" in report
