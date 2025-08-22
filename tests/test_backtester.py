"""
Tests for the Backtester service.
"""
import pytest
import pandas as pd
from services.backtester import Backtester
from core.models import BacktestSettings
from core.strategy import SmaCross


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """
    Creates a sample dataframe for backtesting.
    This data is designed to trigger a crossover.
    """
    index = pd.date_range(start="2020-01-01", periods=250)
    return pd.DataFrame({
        'Open': [100 + i for i in range(250)],
        'High': [100 + i for i in range(250)],
        'Low': [100 + i for i in range(250)],
        'Close': [100 + i for i in range(250)],
        'Volume': [1000 for _ in range(250)]
    }, index=index)


def test_backtester_run(sample_data: pd.DataFrame) -> None:
    """
    Tests that the Backtester service can run a backtest and return results.
    """
    # Arrange
    backtester = Backtester()
    settings = BacktestSettings(cash=100000, commission=0.002, trade_size=0.95)

    # Act
    stats, trades = backtester.run(sample_data, SmaCross, settings)

    # Assert
    assert stats is not None
    assert isinstance(stats, pd.Series)
    assert isinstance(trades, pd.DataFrame)
    assert 'Sharpe Ratio' in stats.index
    assert 'Max. Drawdown [%]' in stats.index
    assert 'Return [%]' in stats.index
