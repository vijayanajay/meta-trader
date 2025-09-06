"""
Service for generating reports from backtest results.
"""
from typing import List, Optional, Dict
import pandas as pd
import numpy as np

from praxis_engine.core.models import (
    BacktestMetrics,
    BacktestSummary,
    Trade,
    Opportunity,
    RunMetadata,
    DrawdownPeriod,
)
from praxis_engine.core.logger import get_logger
from praxis_engine.utils import generate_ascii_histogram
from praxis_engine.services.diagnostics_service import DiagnosticsService

log = get_logger(__name__)

class ReportGenerator:
    """
    Generates reports from a list of trades.
    """

    def generate_backtest_report(
        self,
        trades_df: pd.DataFrame,
        metrics: BacktestMetrics,
        start_date: str,
        end_date: str,
        metadata: Optional[RunMetadata] = None,
    ) -> str:
        """
        Generates a summary report from a DataFrame of trades.
        """
        if trades_df.empty:
            return "## Backtest Report\n\nNo trades were executed."

        kpis = self._calculate_kpis(trades_df, start_date, end_date)
        funnel_table = self._generate_filtering_funnel_table(metrics)
        rejection_table = self._generate_rejection_analysis_table(
            metrics.rejections_by_guard
        )

        metadata_section = ""
        if metadata:
            metadata_section = f"""
### Run Configuration & Metadata
| Parameter | Value |
| --- | --- |
| Run Timestamp | {metadata.run_timestamp} |
| Config File | `{metadata.config_path}` |
| Git Commit Hash | `{metadata.git_commit_hash}` |
"""

        trade_returns_pct = trades_df["net_return_pct"].tolist()
        histogram = generate_ascii_histogram([r * 100 for r in trade_returns_pct])

        report = f"""
## Backtest Report
{metadata_section}
**Period:** {start_date} to {end_date}
**Total Trades:** {len(trades_df)}

{funnel_table}
{rejection_table}

### Key Performance Indicators
| Metric | Value |
| --- | --- |
| Net Annualized Return | {kpis['net_annualized_return']:.2%} |
| Sharpe Ratio | {kpis['sharpe_ratio']:.2f} |
| Profit Factor | {kpis['profit_factor']:.2f} |
| Maximum Drawdown | {kpis['max_drawdown']:.2%} |
| Win Rate | {kpis['win_rate']:.2%} |

### Trade Distribution Analysis
| Metric | Value |
| --- | --- |
| Avg. Holding Period | {kpis['avg_holding_period_days']:.2f} days |
| Avg. Win | {kpis['avg_win_pct']:.2%} |
| Avg. Loss | {kpis['avg_loss_pct']:.2%} |
| Best Trade | {kpis['best_trade_pct']:.2%} |
| Worst Trade | {kpis['worst_trade_pct']:.2%} |
| Skewness | {kpis['skewness']:.2f} |
| Kurtosis | {kpis['kurtosis']:.2f} |

### Net Return (%) Distribution
```
{histogram}
```
"""
        drawdown_period = DiagnosticsService.analyze_drawdown(trades_df)
        drawdown_section = self._generate_drawdown_analysis_section(
            trades_df, drawdown_period
        )
        report += drawdown_section

        return report

    def _generate_drawdown_analysis_section(
        self, trades_df: pd.DataFrame, drawdown_period: Optional[DrawdownPeriod]
    ) -> str:
        """Generates the Maximum Drawdown Analysis markdown section."""
        if not drawdown_period:
            return "\n### Maximum Drawdown Analysis\n\nCould not determine drawdown period."

        section = f"""
### Maximum Drawdown Analysis
**Period:** {drawdown_period.start_date.date()} to {drawdown_period.end_date.date()}
**Max Drawdown:** {drawdown_period.max_drawdown_pct:.2%} (Equity dropped from {drawdown_period.peak_value:.2f} to {drawdown_period.trough_value:.2f})

**Trades within this period:**
"""
        drawdown_trades = trades_df.loc[drawdown_period.trade_indices]

        if drawdown_trades.empty:
            return section + "\nNo trades found within the maximum drawdown period."

        # Summary table of trades in the drawdown
        summary = (
            drawdown_trades.groupby("exit_reason")["net_return_pct"]
            .agg(["count", "sum"])
            .rename(columns={"sum": "total_return_pct"})
        )
        summary["total_return_pct"] = summary["total_return_pct"].apply(
            lambda x: f"{x:.2%}"
        )

        section += summary.to_markdown()
        return section

    def _calculate_kpis(
        self, trades_df: pd.DataFrame, start_date: str, end_date: str
    ) -> dict[str, float]:
        """
        Calculates KPIs from a DataFrame of trades using vectorized operations.
        """
        if trades_df.empty:
            return {k: 0.0 for k in [
                "net_annualized_return", "sharpe_ratio", "profit_factor",
                "max_drawdown", "win_rate", "avg_holding_period_days",
                "avg_win_pct", "avg_loss_pct", "best_trade_pct",
                "worst_trade_pct", "skewness", "kurtosis"
            ]}

        returns_pct = trades_df["net_return_pct"]
        wins = returns_pct[returns_pct > 0]
        losses = returns_pct[returns_pct < 0]

        total_profit = wins.sum()
        total_loss = losses.abs().sum()

        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        win_rate = len(wins) / len(trades_df) if not trades_df.empty else 0

        # Create a daily equity series
        trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"])
        daily_returns = (
            trades_df.groupby(trades_df["exit_date"].dt.date)["net_return_pct"]
            .mean()
            .reindex(pd.date_range(start=start_date, end=end_date, freq="D"), fill_value=0.0)
        )

        equity_curve = (1 + daily_returns).cumprod()
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()

        total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
        total_return = equity_curve.iloc[-1] - 1
        annualized_return = (
            ((1 + total_return) ** (365.25 / total_days) - 1) if total_days > 0 else 0
        )
        sharpe_ratio = (
            (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            if daily_returns.std() != 0
            else 0
        )

        return {
            "net_annualized_return": float(annualized_return),
            "sharpe_ratio": float(sharpe_ratio),
            "profit_factor": float(profit_factor),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "avg_holding_period_days": float(trades_df["holding_period_days"].mean()),
            "avg_win_pct": float(wins.mean()),
            "avg_loss_pct": float(losses.mean()),
            "best_trade_pct": float(returns_pct.max()),
            "worst_trade_pct": float(returns_pct.min()),
            "skewness": float(returns_pct.skew()),
            "kurtosis": float(returns_pct.kurt()),
        }

    def _generate_filtering_funnel_table(self, metrics: BacktestMetrics) -> str:
        """Generates the filtering funnel markdown table."""
        total_rejections_by_guard = sum(metrics.rejections_by_guard.values())
        survived_guards = metrics.potential_signals - total_rejections_by_guard
        survived_llm = survived_guards - metrics.rejections_by_llm

        if metrics.potential_signals == 0:
            return "### Filtering Funnel\n\nNo potential signals were generated."

        pct_survived_guards = (survived_guards / metrics.potential_signals) * 100
        pct_survived_llm = (
            (survived_llm / survived_guards) * 100 if survived_guards > 0 else 0
        )
        pct_executed = (
            (metrics.trades_executed / survived_llm) * 100 if survived_llm > 0 else 0
        )

        table = f"""
### Filtering Funnel
| Stage | Count | % of Previous Stage |
| --- | --- | --- |
| Potential Signals | {metrics.potential_signals} | 100.00% |
| Survived Guardrails | {survived_guards} | {pct_survived_guards:.2f}% |
| Survived LLM Audit | {survived_llm} | {pct_survived_llm:.2f}% |
| Trades Executed | {metrics.trades_executed} | {pct_executed:.2f}% |
"""
        return table

    def _generate_rejection_analysis_table(self, rejections: Dict[str, int]) -> str:
        """Generates the guardrail rejection analysis markdown table."""
        if not rejections:
            return "### Guardrail Rejection Analysis\n\nNo signals were rejected by guardrails."

        total_rejections = sum(rejections.values())
        header = "| Guardrail | Rejection Count | % of Total Guard Rejections |\n"
        separator = "| --- | --- | --- |\n"
        rows = [
            f"| {guard} | {count} | {(count / total_rejections) * 100:.2f}% |"
            for guard, count in sorted(
                rejections.items(), key=lambda item: item[1], reverse=True
            )
        ]

        table = f"""
### Guardrail Rejection Analysis
{header}{separator}{"\\n".join(rows)}
"""
        return table

    def generate_opportunities_report(self, opportunities: List[Opportunity]) -> str:
        """
        Generates a markdown report for new trading opportunities.
        """
        if not opportunities:
            return "## Weekly Opportunities Report\n\nNo new high-confidence opportunities found."

        header = "| Stock | Signal Date | Entry Price | Stop-Loss | Confidence Score |\n"
        separator = "|---|---|---|---|---|\n"
        rows = [
            f"| {opp.stock} | {opp.signal_date.date()} | {opp.signal.entry_price:.2f} | {opp.signal.stop_loss:.2f} | {opp.confidence_score:.2f} |"
            for opp in opportunities
        ]

        return (
            "## Weekly Opportunities Report\n\n" + header + separator + "\n".join(rows)
        )

    def generate_per_stock_report(
        self,
        per_stock_metrics: Dict[str, BacktestMetrics],
        per_stock_trades: Dict[str, List[Dict]],
    ) -> str:
        """
        Generates a markdown report for the per-stock performance breakdown.
        """
        if not per_stock_metrics:
            return "### Per-Stock Performance Breakdown\n\nNo per-stock data available."

        header = "| Stock | Compounded Return | Total Trades | Potential Signals | Rejections by Guard | Rejections by LLM |\n"
        separator = "|---|---|---|---|---|---|\n"
        rows = []
        for stock, metrics in per_stock_metrics.items():
            trades_list = per_stock_trades.get(stock, [])
            if trades_list:
                trades_df = pd.DataFrame(trades_list)
                trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"])
                trades_df = trades_df.sort_values(by="exit_date")
                multiplier = (1.0 + trades_df["net_return_pct"]).prod()
                compounded_return = (multiplier - 1.0) * 100.0
            else:
                compounded_return = 0.0

            rejections_by_guard = sum(metrics.rejections_by_guard.values())
            row = f"| {stock} | {compounded_return:.2f}% | {metrics.trades_executed} | {metrics.potential_signals} | {rejections_by_guard} | {metrics.rejections_by_llm} |"
            rows.append(row)

        return (
            "### Per-Stock Performance Breakdown\n\n"
            + header
            + separator
            + "\n".join(rows)
        )

    def generate_sensitivity_report(
        self, results: List[BacktestSummary], parameter_name: str
    ) -> str:
        """
        Generates a markdown report for a sensitivity analysis run.
        """
        if not results:
            return f"## Sensitivity Analysis Report for '{parameter_name}'\n\nNo results to report."

        header = f"| {parameter_name} | Total Trades | Win Rate (%) | Profit Factor | Avg Net Return (%) | Std Dev Return (%) |\n"
        separator = "|---|---|---|---|---|---|\n"
        rows = [
            f"| {res.parameter_value:.4f} | {res.total_trades} | {res.win_rate_pct:.2f} | {res.profit_factor:.2f} | {res.net_return_pct_mean:.2f} | {res.net_return_pct_std:.2f} |"
            for res in results
        ]

        # Sort results by the parameter value for clarity
        rows.sort(key=lambda x: float(x.split('|')[1].strip()))

        return (
            f"## Sensitivity Analysis Report for '{parameter_name}'\n\n"
            + header
            + separator
            + "\n".join(rows)
        )
