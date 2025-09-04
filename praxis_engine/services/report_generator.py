"""
Service for generating reports from backtest results.
"""
from typing import List, Optional, Dict
import pandas as pd
import numpy as np

from praxis_engine.core.models import BacktestMetrics, BacktestSummary, Trade, Opportunity, RunMetadata
from praxis_engine.core.logger import get_logger
from praxis_engine.utils import generate_ascii_histogram

log = get_logger(__name__)

class ReportGenerator:
    """
    Generates reports from a list of trades.
    """

    def generate_backtest_report(
        self,
        trades: List[Trade],
        metrics: BacktestMetrics,
        start_date: str,
        end_date: str,
        metadata: Optional[RunMetadata] = None,
    ) -> str:
        """
        Generates a summary report from a list of trades.
        """
        if not trades:
            return "## Backtest Report\n\nNo trades were executed."

        kpis = self._calculate_kpis(trades, start_date, end_date)
        funnel_table = self._generate_filtering_funnel_table(metrics)
        rejection_table = self._generate_rejection_analysis_table(metrics.rejections_by_guard)


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

        trade_returns_pct = [t.net_return_pct for t in trades]
        histogram = generate_ascii_histogram([r * 100 for r in trade_returns_pct])


        report = f"""
## Backtest Report
{metadata_section}
**Period:** {start_date} to {end_date}
**Total Trades:** {len(trades)}

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
        return report

    def _calculate_kpis(self, trades: List[Trade], start_date: str, end_date: str) -> dict[str, float]:
        """
        Calculates the key performance indicators for the backtest.
        """
        returns_pct = [trade.net_return_pct for trade in trades]

        # Profit Factor & Win Rate
        wins = [r for r in returns_pct if r > 0]
        losses = [r for r in returns_pct if r < 0]

        profit_factor = sum(wins) / abs(sum(losses)) if losses else float('inf')
        win_rate = len(wins) / len(trades) if trades else 0

        # Create a daily equity series to calculate portfolio-level stats
        trade_dates = [trade.exit_date for trade in trades]
        trade_returns = pd.Series(returns_pct, index=trade_dates)

        # Create a full date range for the backtest period
        full_date_range = pd.to_datetime(pd.date_range(start=start_date, end=end_date))

        # Create a daily portfolio return series
        daily_returns = pd.Series(0.0, index=full_date_range, dtype="float64")
        # This is a simplification. A real implementation would allocate capital.
        # For now, we assume each trade uses an equal portion of capital,
        # so the daily return is the average of returns on that day.
        daily_returns.update(trade_returns.groupby(trade_returns.index).mean())

        equity_curve = (1 + daily_returns).cumprod()

        # Net Annualized Return
        total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
        total_return = equity_curve.iloc[-1] - 1
        annualized_return = (1 + total_return) ** (365.25 / total_days) - 1 if total_days > 0 else 0

        # Sharpe Ratio
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() != 0 else 0

        # Max Drawdown
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()

        # Trade distribution stats
        holding_periods = [(trade.exit_date - trade.entry_date).days for trade in trades]
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0
        avg_win_pct = np.mean(wins) if wins else 0
        avg_loss_pct = np.mean(losses) if losses else 0
        best_trade_pct = max(returns_pct) if returns_pct else 0
        worst_trade_pct = min(returns_pct) if returns_pct else 0
        skewness = pd.Series(returns_pct).skew() if returns_pct else 0
        kurtosis = pd.Series(returns_pct).kurt() if returns_pct else 0


        return {
            "net_annualized_return": float(annualized_return),
            "sharpe_ratio": float(sharpe_ratio),
            "profit_factor": float(profit_factor),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "avg_holding_period_days": float(avg_holding_period),
            "avg_win_pct": float(avg_win_pct),
            "avg_loss_pct": float(avg_loss_pct),
            "best_trade_pct": float(best_trade_pct),
            "worst_trade_pct": float(worst_trade_pct),
            "skewness": float(skewness),
            "kurtosis": float(kurtosis),
        }

    def _generate_filtering_funnel_table(self, metrics: BacktestMetrics) -> str:
        """Generates the filtering funnel markdown table."""
        total_rejections_by_guard = sum(metrics.rejections_by_guard.values())
        survived_guards = metrics.potential_signals - total_rejections_by_guard
        survived_llm = survived_guards - metrics.rejections_by_llm

        if metrics.potential_signals == 0:
            return "### Filtering Funnel\n\nNo potential signals were generated."

        pct_survived_guards = (survived_guards / metrics.potential_signals) * 100
        pct_survived_llm = (survived_llm / survived_guards) * 100 if survived_guards > 0 else 0
        pct_executed = (metrics.trades_executed / survived_llm) * 100 if survived_llm > 0 else 0

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
            for guard, count in sorted(rejections.items(), key=lambda item: item[1], reverse=True)
        ]

        table = f"""
### Guardrail Rejection Analysis
{header}{separator}{"\\n".join(rows)}
"""
        return table

    def generate_opportunities_report(
        self, opportunities: List[Opportunity]
    ) -> str:
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
            "## Weekly Opportunities Report\n\n"
            + header
            + separator
            + "\n".join(rows)
        )

    def generate_per_stock_report(
        self,
        per_stock_metrics: Dict[str, BacktestMetrics],
        per_stock_trades: Dict[str, List[Trade]],
    ) -> str:
        """
        Generates a markdown report for the per-stock performance breakdown.
        """
        if not per_stock_metrics:
            return "### Per-Stock Performance Breakdown\n\nNo per-stock data available."

        # Show compounded total return per stock (not mean per-trade return).
        # This aligns with the project's requirement to report reproducible,
        # economically-meaningful metrics (see HARD_RULES.md).
        header = "| Stock | Compounded Return | Total Trades | Potential Signals | Rejections by Guard | Rejections by LLM |\n"
        separator = "|---|---|---|---|---|---|\n"
        rows = []
        for stock, metrics in per_stock_metrics.items():
            trades = per_stock_trades.get(stock, [])
            # Calculate compounded return from time-ordered trades. Each trade.net_return_pct
            # is expressed as a decimal (e.g., 0.02 for +2%). We compute the product
            # of (1 + r) across trades to get total compounded multiplier, then
            # subtract 1 and convert to percentage for display.
            if trades:
                # Ensure trades are ordered by exit date to avoid leakage
                trades_sorted = sorted(trades, key=lambda t: t.exit_date)
                multiplier = 1.0
                for tr in trades_sorted:
                    multiplier *= (1.0 + tr.net_return_pct)
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
