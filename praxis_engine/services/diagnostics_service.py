from typing import Optional, List
import pandas as pd
from praxis_engine.core.models import DrawdownPeriod

class DiagnosticsService:
    @staticmethod
    def analyze_drawdown(trades_df: pd.DataFrame) -> Optional[DrawdownPeriod]:
        """
        Analyzes a DataFrame of trades to find the maximum drawdown period.

        Args:
            trades_df: A DataFrame containing trade data, must include
                       'exit_date' and 'net_return_pct' columns.

        Returns:
            A DrawdownPeriod object containing details of the max drawdown,
            or None if no trades or no drawdown is found.
        """
        if trades_df.empty:
            return None

        df = trades_df.sort_values(by="exit_date").reset_index()

        # Prepend an initial equity of 1.0 to correctly handle drawdowns from the start
        initial_equity = pd.Series([1.0])
        trade_equity = (1 + df["net_return_pct"]).cumprod()
        equity_curve = pd.concat([initial_equity, trade_equity], ignore_index=True)

        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max

        if not (drawdown < 0).any():
            return None

        trough_idx = drawdown.idxmin()
        peak_idx = equity_curve.loc[:trough_idx].idxmax()

        peak_value = equity_curve[peak_idx]
        trough_value = equity_curve[trough_idx]

        # The indices from equity_curve are offset by 1 from the df indices
        # because we prepended the initial equity.
        start_idx_df = peak_idx - 1
        end_idx_df = trough_idx - 1

        # If peak is the initial capital, the drawdown starts before the first trade.
        # We take the date of the first trade in the drawdown period as the start date.
        if peak_idx == 0:
            start_date = df.loc[0, "exit_date"]
            # The trades involved are from the beginning up to the trough
            trade_indices = df.loc[0:end_idx_df, "index"].tolist()
        else:
            start_date = df.loc[start_idx_df, "exit_date"]
            trade_indices = df.loc[start_idx_df:end_idx_df, "index"].tolist()

        return DrawdownPeriod(
            start_date=start_date,
            end_date=df.loc[end_idx_df, "exit_date"],
            peak_value=peak_value,
            trough_value=trough_value,
            max_drawdown_pct=(trough_value - peak_value) / peak_value,
            trade_indices=trade_indices,
        )
