"""
Tests for the strategy classes.
"""
import pandas as pd
from backtesting import Backtest
from core.strategy import SmaCross


def test_sma_cross_initialization() -> None:
    """
    Tests that the SmaCross strategy can be initialized without errors.
    """
    # Create a dummy dataframe
    index = pd.date_range(start="2020-01-01", periods=250)
    data = pd.DataFrame({
        'Open': [100 + i for i in range(250)],
        'High': [100 + i for i in range(250)],
        'Low': [100 + i for i in range(250)],
        'Close': [100 + i for i in range(250)],
        'Volume': [1000 for _ in range(250)]
    }, index=index)

    # Instantiate the backtest with the strategy
    bt = Backtest(data, SmaCross, cash=10000, commission=.002)

    # Run the backtest
    bt.run()

    # Assert that the strategy was initialized
    assert bt._strategy is not None
    assert bt._strategy is SmaCross
