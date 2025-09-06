import pandas as pd
from typing import Optional, List

from praxis_engine.core.models import DrawdownPeriod


class DiagnosticsService:
    """
    A service for performing diagnostic analyses on backtest results.
    """

    @staticmethod
    def analyze_drawdown(trades_df: pd.DataFrame) -> Optional[DrawdownPeriod]:
        """
        Analyzes a DataFrame of trades to find the most significant drawdown period.

        Args:
            trades_df: A DataFrame containing trade data, must include
                       'exit_date' and 'net_return_pct' columns.

        Returns:
            A DrawdownPeriod object representing the largest drawdown, or None
            if no trades are provided.
        """
        if trades_df.empty:
            return None

        # Ensure dataframe is sorted by exit date for accurate cumulative calculations
        df = trades_df.sort_values(by="exit_date").reset_index()

        # Calculate equity curve and drawdowns
        df["equity_curve"] = (1 + df["net_return_pct"]).cumprod()
        df["running_max"] = df["equity_curve"].cummax()
        df["drawdown"] = (df["equity_curve"] - df["running_max"]) / df[
            "running_max"
        ]

        # Find the end of the maximum drawdown period (the trough)
        trough_idx = df["drawdown"].idxmin()
        trough_date = df.loc[trough_idx, "exit_date"]
        trough_value = df.loc[trough_idx, "equity_curve"]

        # Find the start of the maximum drawdown period (the peak before the trough)
        peak_idx = df.loc[:trough_idx, "equity_curve"].idxmax()
        peak_date = df.loc[peak_idx, "exit_date"]
        peak_value = df.loc[peak_idx, "equity_curve"]

        max_drawdown_pct = df.loc[trough_idx, "drawdown"]

        # Get the original indices of the trades within this period
        trade_indices = df.loc[peak_idx:trough_idx, "index"].tolist()

        return DrawdownPeriod(
            start_date=peak_date,
            end_date=trough_date,
            peak_value=peak_value,
            trough_value=trough_value,
            max_drawdown_pct=max_drawdown_pct,
            trade_indices=trade_indices,
        )
