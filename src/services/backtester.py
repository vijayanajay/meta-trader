"""
Service for running trading strategy backtests.
"""
import pandas as pd
from typing import Any, Type
from backtesting import Strategy

__all__ = ["Backtester"]


class Backtester:
    """
    A thin wrapper around the backtesting.py library to execute backtests.
    """
    def __init__(self) -> None:
        pass

    def run(self, data: pd.DataFrame, strategy_class: Type[Strategy]) -> Any:
        """
        Runs a backtest for a given strategy class on the provided data.

        Returns:
            The results object from the backtesting library.
        """
        # This is a placeholder implementation.
        print(f"Running backtest for strategy: {strategy_class.__name__}...")
        return None
