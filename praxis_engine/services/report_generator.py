"""
Service for generating reports from backtest results.
"""
from typing import List
import pandas as pd
import numpy as np

from praxis_engine.core.models import BacktestSummary, Trade, Opportunity

class ReportGenerator:
    """
    Generates reports from a list of trades.
    """

    def generate_backtest_report(self, trades: List[Trade], start_date: str, end_date: str) -> str:
        """
        Generates a summary report from a list of trades.
        """
        if not trades:
            return "## Backtest Report\n\nNo trades were executed."

        # Placeholder for KPI calculations
        kpis = self._calculate_kpis(trades, start_date, end_date)

        report = f"""
## Backtest Report

**Period:** {start_date} to {end_date}
**Total Trades:** {len(trades)}

### Key Performance Indicators
| Metric | Value |
| --- | --- |
| Net Annualized Return | {kpis['net_annualized_return']:.2%} |
| Sharpe Ratio | {kpis['sharpe_ratio']:.2f} |
| Profit Factor | {kpis['profit_factor']:.2f} |
| Maximum Drawdown | {kpis['max_drawdown']:.2%} |
| Win Rate | {kpis['win_rate']:.2%} |

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

        return {
            "net_annualized_return": annualized_return,
            "sharpe_ratio": sharpe_ratio,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
        }

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
