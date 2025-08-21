"""
Defines the baseline trading strategies for the quant engine.
"""
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover
import pandas_ta as ta


class SmaCross(Strategy):  # type: ignore[misc]
    """
    A simple moving average crossover strategy.

    This strategy is used as the baseline (Iteration 0) for the LLM
    to improve upon. It goes long when a short-term SMA crosses
    above a long-term SMA and goes short when the opposite occurs.
    """
    # Define the two MA lags as class variables
    n1 = 50
    n2 = 200

    def init(self) -> None:
        """
        Initialize the strategy indicators.
        """
        # Pre-compute the two moving averages
        close_series = pd.Series(self.data.Close)
        self.sma1 = self.I(ta.sma, close_series, self.n1)
        self.sma2 = self.I(ta.sma, close_series, self.n2)

    def next(self) -> None:
        """
        Define the strategy logic for the next tick.
        """
        # If the short-term MA crosses above the long-term MA, buy
        if crossover(self.sma1, self.sma2):
            self.buy()

        # If the short-term MA crosses below the long-term MA, sell
        elif crossover(self.sma2, self.sma1):
            self.sell()
