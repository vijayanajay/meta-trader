"""
This service is responsible for generating structured performance reports
from the raw results of a backtest.
"""
import pandas as pd
import numpy as np

from core.models import (
    StrategyDefinition,
    TradeSummary,
    PerformanceReport,
    PerformanceMetrics,
)

__all__ = ["ReportGenerator"]


class ReportGenerator:
    """
    Translates backtesting.py results into a structured PerformanceReport.
    Adheres to the structure specified in PRD (FR4).
    """

    @staticmethod
    def _calculate_trade_summary(trades: pd.DataFrame) -> TradeSummary:
        """
        Calculates the information-dense statistical trade summary.
        """
        if trades.empty:
            return TradeSummary(
                total_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                avg_win_pct=0.0,
                avg_loss_pct=0.0,
                max_consecutive_losses=0,
                avg_trade_duration_bars=0,
            )

        total_trades = len(trades)
        winning_trades = trades[trades["ReturnPct"] > 0]
        losing_trades = trades[trades["ReturnPct"] < 0]

        win_rate_pct = (len(winning_trades) / total_trades) * 100

        total_profit = winning_trades["ReturnPct"].sum()
        total_loss = abs(losing_trades["ReturnPct"].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else np.inf

        # Calculate max consecutive losses
        max_consecutive_losses = 0
        current_consecutive_losses = 0
        for pnl in trades["ReturnPct"]:
            if pnl < 0:
                current_consecutive_losses += 1
            else:
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
                current_consecutive_losses = 0
        max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)


        return TradeSummary(
            total_trades=total_trades,
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            avg_win_pct=winning_trades["ReturnPct"].mean() * 100,
            avg_loss_pct=losing_trades["ReturnPct"].mean() * 100,
            max_consecutive_losses=max_consecutive_losses,
            avg_trade_duration_bars=int(trades["Duration"].dt.days.mean()),
        )

    @staticmethod
    def generate(
        stats: pd.Series,
        trades: pd.DataFrame,
        strategy_def: StrategyDefinition,
    ) -> PerformanceReport:
        """
        Creates a PerformanceReport from backtest statistics.

        Args:
            stats: The summary statistics Series from a backtesting.py run.
                     Expected to contain keys like 'Sharpe Ratio', 'Sortino Ratio',
                     'Max. Drawdown [%]', 'Return (Ann.) [%]'.
            trades: The DataFrame of trades from a backtesting.py run.
            strategy_def: The definition of the strategy that was run.

        Returns:
            A populated PerformanceReport object.
        """
        trade_summary = ReportGenerator._calculate_trade_summary(trades)

        performance_metrics = PerformanceMetrics(
            sharpe_ratio=stats.get("Sharpe Ratio", 0.0),
            sortino_ratio=stats.get("Sortino Ratio", 0.0),
            max_drawdown_pct=stats.get("Max. Drawdown [%]", 0.0),
            annual_return_pct=stats.get("Return (Ann.) [%]", 0.0),
        )

        return PerformanceReport(
            strategy=strategy_def,
            performance=performance_metrics,
            trade_summary=trade_summary,
        )
