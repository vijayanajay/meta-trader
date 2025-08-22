import pandas as pd
import pytest
from backtesting import Strategy

from core.models import StrategyDefinition, Indicator
from services.strategy_engine import StrategyEngine

@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Fixture for sample OHLCV data."""
    # Create enough data for ADX period
    data = {
        'Open': [i for i in range(100)],
        'High': [i + 2 for i in range(100)],
        'Low': [i - 2 for i in range(100)],
        'Close': [i + 1 for i in range(100)],
        'Volume': [1000 for _ in range(100)],
    }
    return pd.DataFrame(data)

def test_process_with_adx_indicator(sample_data: pd.DataFrame) -> None:
    """
    Tests that the StrategyEngine can correctly process a strategy definition
    that uses the ADX indicator, which is a multi-column indicator.
    """
    # Arrange
    strategy_def = StrategyDefinition(
        strategy_name="ADX_Test",
        indicators=[
            Indicator(name="adx", function="adx", params={"length": 14})
        ],
        buy_condition="adx > 20",
        sell_condition="adx < 10"
    )
    engine = StrategyEngine()

    # Act
    try:
        strategy_class = engine.process(
            data=sample_data,
            strategy_def=strategy_def,
            trade_size=1.0
        )
    except ValueError as e:
        pytest.fail(f"StrategyEngine failed to process ADX indicator: {e}")

    # Assert
    assert issubclass(strategy_class, Strategy)
    # The main assertion is that no NameError or ValueError was raised.
    # We can also inspect the created class if needed, but for this test,
    # successful creation is sufficient to validate the fix.
    assert hasattr(strategy_class, 'init')
    assert hasattr(strategy_class, 'next')
    assert hasattr(strategy_class, 'trade_size_param')
    assert strategy_class.trade_size_param == 1.0
