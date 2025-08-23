"""
Service for simulating trade execution and calculating returns.
"""
from typing import Optional
import pandas as pd

from praxis_engine.core.models import Signal, Trade
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

class ExecutionSimulator:
    """
    Simulates the execution of a trade and calculates its outcome.
    """

    def simulate_trade(
        self,
        stock: str,
        df: pd.DataFrame,
        signal: Signal,
        entry_index: int,
        confidence_score: float
    ) -> Optional[Trade]:
        """
        Simulates a single trade based on a signal.

        Args:
            stock: The stock ticker.
            df: The full historical data DataFrame.
            signal: The signal to execute.
            entry_index: The integer index in the df for trade entry.
            confidence_score: The confidence score from the LLM audit.

        Returns:
            A Trade object with the outcome, or None if exit is out of bounds.
        """
        entry_date = df.index[entry_index]
        entry_price = df["Open"].iloc[entry_index] # Enter on next day's open

        exit_index = entry_index + signal.exit_target_days
        if exit_index >= len(df):
            log.warning(f"Cannot simulate trade for {stock} on {entry_date}: exit is out of bounds.")
            return None

        exit_date = df.index[exit_index]
        exit_price = df["Close"].iloc[exit_index] # Exit on the close of the target day

        # Simple net return for now, ignoring detailed costs.
        net_return_pct = (exit_price / entry_price) - 1.0

        return Trade(
            stock=stock,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            net_return_pct=net_return_pct,
            confidence_score=confidence_score
        )
