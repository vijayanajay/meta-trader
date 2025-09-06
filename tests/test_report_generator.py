import pandas as pd
import pytest
from typing import List, Dict

from praxis_engine.core.models import (
    BacktestMetrics,
    BacktestSummary,
    Trade,
    Signal,
    RunMetadata,
)
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
def sample_trades_df() -> pd.DataFrame:
    """
    Provides a sample DataFrame of trades for testing.
    """
    trades_data = [
        {
            "stock": "RELIANCE.NS",
            "entry_date": pd.Timestamp("2023-01-02"),
            "exit_date": pd.Timestamp("2023-01-22"),
            "holding_period_days": 20,
            "net_return_pct": 0.10,
            "exit_reason": "PROFIT_TARGET",
            "composite_score": 0.7,
            "entry_sector_vol": 15.0,
        },
        {
            "stock": "RELIANCE.NS",
            "entry_date": pd.Timestamp("2023-02-01"),
            "exit_date": pd.Timestamp("2023-02-21"),
            "holding_period_days": 20,
            "net_return_pct": -0.05,
            "exit_reason": "ATR_STOP_LOSS",
            "composite_score": 0.6,
            "entry_sector_vol": 20.0,
        },
    ]
    return pd.DataFrame(trades_data)


def test_generate_backtest_report_no_trades(
    report_generator: ReportGenerator, sample_metrics: BacktestMetrics
) -> None:
    """
    Tests that the report generator handles the case with no trades.
    """
    report = report_generator.generate_backtest_report(
        pd.DataFrame(), sample_metrics, "2023-01-01", "2023-12-31"
    )
    assert "No trades were executed" in report


def test_generate_backtest_report_with_metadata(
    report_generator: ReportGenerator,
    sample_trades_df: pd.DataFrame,
    sample_metrics: BacktestMetrics,
) -> None:
    """
    Tests that the report generator correctly renders the metadata section.
    """
    metadata = RunMetadata(
        run_timestamp="2025-08-30 12:00:00 UTC",
        config_path="config.ini",
        git_commit_hash="abcdef1",
    )
    report = report_generator.generate_backtest_report(
        sample_trades_df, sample_metrics, "2023-01-01", "2023-12-31", metadata=metadata
    )

    assert "Run Configuration & Metadata" in report
    assert "### Trade Distribution Analysis" in report
    assert "### Net Return (%) Distribution" in report


def test_calculate_kpis_with_sample_data(
    report_generator: ReportGenerator, sample_trades_df: pd.DataFrame
) -> None:
    """
    Tests the KPI calculations with a sample set of trades.
    """
    start_date = "2023-01-01"
    end_date = "2023-03-31"
    kpis = report_generator._calculate_kpis(sample_trades_df, start_date, end_date)

    assert kpis["win_rate"] == pytest.approx(0.5)
    assert kpis["profit_factor"] == pytest.approx(2.0) # 0.10 / |-0.05|
    assert kpis["avg_holding_period_days"] == pytest.approx(20.0)
    assert kpis["avg_win_pct"] == pytest.approx(0.10)
    assert kpis["avg_loss_pct"] == pytest.approx(-0.05)
    assert kpis["best_trade_pct"] == pytest.approx(0.10)
    assert kpis["worst_trade_pct"] == pytest.approx(-0.05)


def test_generate_per_stock_report(
    report_generator: ReportGenerator, sample_metrics: BacktestMetrics
) -> None:
    """
    Tests the generation of the per-stock report.
    """
    per_stock_metrics = {"STOCKA": sample_metrics, "STOCKB": BacktestMetrics()}
    per_stock_trades = {
        "STOCKA": [
            {"net_return_pct": 0.10, "exit_date": "2023-01-22"},
            {"net_return_pct": -0.05, "exit_date": "2023-02-21"},
        ],
        "STOCKB": [],
    }

    report = report_generator.generate_per_stock_report(
        per_stock_metrics, per_stock_trades
    )

    assert "### Per-Stock Performance Breakdown" in report
    # Compounded return: (1 + 0.10) * (1 - 0.05) - 1 = 1.1 * 0.95 - 1 = 1.045 - 1 = 0.045
    assert "| STOCKA | 4.50% | 2 | 10 | 3 | 1 |" in report
    assert "| STOCKB | 0.00% | 0 | 0 | 0 | 0 |" in report


def test_generate_backtest_report_with_drawdown_section(
    report_generator: ReportGenerator,
    sample_trades_with_drawdown: pd.DataFrame,
    sample_metrics: BacktestMetrics,
) -> None:
    """
    Tests that the drawdown analysis section is correctly generated in the report.
    """
    report = report_generator.generate_backtest_report(
        sample_trades_with_drawdown,
        sample_metrics,
        "2023-01-01",
        "2023-01-31",
    )

    assert "### Maximum Drawdown Analysis" in report
    # Drawdown is (0.9801 - 1.21) / 1.21 = -0.19
    assert "| Max Drawdown | -19.00% |" in report
    assert "| Period | 2023-01-03 to 2023-01-05 |" in report
    assert "| Trade Count | 3 |" in report
    assert "- **ATR_STOP_LOSS:** 2" in report
    assert "- **PROFIT_TARGET:** 1" in report
