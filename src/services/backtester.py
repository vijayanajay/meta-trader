"""
This service wraps the backtesting.py library to provide a simple interface
for running backtests on trading strategies.
"""
from typing import Type
import pandas as pd
from backtesting import Backtest, Strategy

# Define a type alias for the results series for clarity
BacktestResult = pd.Series

__all__ = ["Backtester"]


class Backtester:
    """
    A wrapper for the backtesting.py library.
    """

    def run(
        self,
        data: pd.DataFrame,
        strategy_class: Type[Strategy],
        cash: int = 100_000,
        commission: float = 0.002,
    ) -> BacktestResult:
        """
        Runs a backtest for a given strategy and dataset.

        Args:
            data: A pandas DataFrame containing the OHLCV data.
            strategy_class: The strategy class to be backtested.
            cash: The initial cash amount for the backtest.
            commission: The commission rate for trades.

        Returns:
            A pandas Series containing the backtest results.
        """
        bt = Backtest(data, strategy_class, cash=cash, commission=commission)
        stats = bt.run()
        return stats
