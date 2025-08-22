import pytest
import pandas as pd
from unittest.mock import patch
from backtesting import Strategy

from core.models import StrategyDefinition, Indicator
from services.strategy_engine import StrategyEngine

@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Provides a sample DataFrame for testing."""
    # Using a longer dataset to ensure indicators can be calculated
    return pd.DataFrame({
        'Open': range(100, 200),
        'High': range(101, 201),
        'Low': range(99, 199),
        'Close': range(100, 200),
        'Volume': range(1000, 1100),
    })

@pytest.fixture
def ema_crossover_def() -> StrategyDefinition:
    """Provides a valid EMA crossover strategy definition."""
    return StrategyDefinition(
        strategy_name="EMA_Crossover",
        indicators=[
            Indicator(name="ema_fast", function="ema", params={"length": 5}),
            Indicator(name="ema_slow", function="ema", params={"length": 10}),
        ],
        buy_condition="crossover(ema_fast, ema_slow)",
        sell_condition="crossover(ema_slow, ema_fast)",
    )

@pytest.fixture
def macd_def() -> StrategyDefinition:
    """Provides a valid MACD strategy definition."""
    return StrategyDefinition(
        strategy_name="MACD_Strategy",
        indicators=[
            Indicator(name="macd", function="macd", params={"fast": 8, "slow": 21, "signal": 5}),
        ],
        buy_condition="macd > macd_signal",
        sell_condition="macd < macd_signal",
    )

def test_process_valid_strategy(sample_data: pd.DataFrame, ema_crossover_def: StrategyDefinition) -> None:
    """Tests that a valid strategy definition is processed correctly."""
    # Arrange
    engine = StrategyEngine()

    # Act
    DynamicStrategy = engine.process(sample_data, ema_crossover_def, trade_size=0.95)

    # Assert
    assert issubclass(DynamicStrategy, Strategy)

def test_process_macd_strategy(sample_data: pd.DataFrame, macd_def: StrategyDefinition) -> None:
    """Tests that a strategy with a multi-column indicator (MACD) is processed correctly."""
    # Arrange
    engine = StrategyEngine()

    # Act
    DynamicStrategy = engine.process(sample_data, macd_def, trade_size=0.95)

    # Assert
    assert issubclass(DynamicStrategy, Strategy)


def test_process_malicious_string(sample_data: pd.DataFrame) -> None:
    """Tests that a malicious string in a condition fails safely."""
    # Arrange
    engine = StrategyEngine()
    malicious_def = StrategyDefinition(
        strategy_name="Malicious",
        indicators=[],
        buy_condition="__import__('os').system('echo pwned')",
        sell_condition="False"
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid expression"):
        engine.process(sample_data, malicious_def, trade_size=0.95)

def test_process_non_existent_indicator(sample_data: pd.DataFrame) -> None:
    """Tests that a condition referencing a non-existent indicator fails gracefully."""
    # Arrange
    engine = StrategyEngine()
    invalid_def = StrategyDefinition(
        strategy_name="Invalid",
        indicators=[
            Indicator(name="ema_fast", function="ema", params={"length": 2}),
        ],
        buy_condition="crossover(ema_fast, non_existent_indicator)",
        sell_condition="False"
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid expression"):
        engine.process(sample_data, invalid_def, trade_size=0.95)

def test_process_invalid_indicator_function(sample_data: pd.DataFrame) -> None:
    """Tests that an invalid indicator function fails gracefully."""
    # Arrange
    engine = StrategyEngine()
    invalid_def = StrategyDefinition(
        strategy_name="Invalid",
        indicators=[
            Indicator(name="ema_fast", function="non_existent_function", params={"length": 2}),
        ],
        buy_condition="False",
        sell_condition="False"
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Failed to process indicator"):
        engine.process(sample_data, invalid_def, trade_size=0.95)

def test_indicator_function_returns_none(sample_data: pd.DataFrame) -> None:
    """Tests that a ValueError is raised if an indicator function returns None."""
    # Arrange
    engine = StrategyEngine()
    strategy_def = StrategyDefinition(
        strategy_name="None_Indicator",
        indicators=[
            Indicator(name="none_indicator", function="ema", params={"length": 5}),
        ],
        buy_condition="False",
        sell_condition="False",
    )

    # Act & Assert
    with patch("pandas_ta.ema", return_value=None):
        with pytest.raises(ValueError, match="Indicator function returned None"):
            engine.process(sample_data, strategy_def, trade_size=0.95)
