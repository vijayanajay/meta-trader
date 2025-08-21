"""
Tests for the Backtester service.
"""
import pytest
import pandas as pd
from services.backtester import Backtester
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

    # Act
    results = backtester.run(sample_data, SmaCross)

    # Assert
    assert results is not None
    assert isinstance(results, pd.Series)
    assert 'Sharpe Ratio' in results.index
    assert 'Max. Drawdown [%]' in results.index
    assert 'Return [%]' in results.index
