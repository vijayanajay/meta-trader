"""
This service wraps the backtesting.py library to provide a simple interface
for running backtests on trading strategies.
"""
from typing import Type, cast, Tuple
import pandas as pd
from backtesting import Backtest, Strategy

from core.models import BacktestSettings

__all__ = ["Backtester"]


class Backtester:
    """
    A wrapper for the backtesting.py library.
    """

    def run(
        self,
        data: pd.DataFrame,
        strategy_class: Type[Strategy],
        settings: BacktestSettings,
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Runs a backtest for a given strategy and dataset.

        Args:
            data: A pandas DataFrame containing the OHLCV data.
            strategy_class: The strategy class to be backtested.
            settings: The backtest configuration settings.

        Returns:
            A tuple containing:
            - A pandas Series with the backtest results.
            - A pandas DataFrame with the list of trades.
        """
        bt = Backtest(
            data,
            strategy_class,
            cash=settings.cash,
            commission=settings.commission,
            finalize_trades=True,
        )
        stats = bt.run()

        # The _trades attribute is not in the official documentation, but it's where
        # the trades DataFrame is stored. We cast the results to satisfy mypy.
        trades = stats["_trades"]
        return cast(pd.Series, stats), cast(pd.DataFrame, trades)
