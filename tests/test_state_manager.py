"""
Tests for the StateManager service.
"""
import json
from pathlib import Path
import pytest
from core.models import RunState, PerformanceReport, StrategyDefinition, TradeSummary, PerformanceMetrics
from services.state_manager import StateManager


@pytest.fixture
def test_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory for test files.
    """
    return tmp_path


@pytest.fixture
def sample_run_state() -> RunState:
    """
    Create a sample RunState object for testing.
    """
    strategy_def = StrategyDefinition(
        strategy_name="Test Strategy",
        indicators=[],
        buy_condition="Close > Open",
        sell_condition="Close < Open",
    )
    trade_summary = TradeSummary(
        total_trades=10,
        win_rate_pct=50.0,
        profit_factor=1.5,
        avg_win_pct=2.0,
        avg_loss_pct=-1.0,
        max_consecutive_losses=3,
        avg_trade_duration_bars=5,
    )
    report = PerformanceReport(
        strategy=strategy_def,
        performance=PerformanceMetrics(
            sharpe_ratio=1.2,
            sortino_ratio=1.8,
            max_drawdown_pct=-15.0,
            annual_return_pct=25.0,
        ),
        trade_summary=trade_summary,
    )
    return RunState(iteration_number=1, history=[report])


def test_save_and_load_state(
    test_dir: Path, sample_run_state: RunState
) -> None:
    """
    Test that the StateManager can save a RunState and load it back correctly.
    """
    # Arrange
    ticker = "TEST_TICKER"
    manager = StateManager(results_dir=test_dir, run_state_file="test_run_state.json")

    # Act
    manager.save_state(ticker, sample_run_state)
    loaded_state = manager.load_state(ticker)

    # Assert
    expected_filepath = test_dir / f"{ticker}_test_run_state.json"
    assert expected_filepath.exists()
    assert loaded_state == sample_run_state
    assert loaded_state.iteration_number == 1
    assert len(loaded_state.history) == 1
    assert loaded_state.history[0].performance.sharpe_ratio == 1.2


def test_load_state_non_existent_file(test_dir: Path) -> None:
    """
    Test that loading a non-existent state file returns a default RunState.
    """
    # Arrange
    ticker = "TEST_TICKER"
    manager = StateManager(results_dir=test_dir, run_state_file="test_run_state.json")

    # Act
    loaded_state = manager.load_state(ticker)

    # Assert
    expected_filepath = test_dir / f"{ticker}_test_run_state.json"
    assert not expected_filepath.exists()
    assert isinstance(loaded_state, RunState)
    assert loaded_state.iteration_number == 0
    assert len(loaded_state.history) == 0


def test_load_state_corrupted_file(test_dir: Path) -> None:
    """
    Test that loading a corrupted JSON file raises a ValueError.
    """
    # Arrange
    ticker = "TEST_TICKER"
    manager = StateManager(results_dir=test_dir, run_state_file="test_run_state.json")
    state_filepath = test_dir / f"{ticker}_test_run_state.json"
    state_filepath.write_text("this is not valid json")

    # Act & Assert
    with pytest.raises(ValueError, match="Error decoding state file"):
        manager.load_state(ticker)


def test_load_state_invalid_schema(test_dir: Path) -> None:
    """
    Test that loading a file with a different schema raises a ValueError.
    """
    # Arrange
    ticker = "TEST_TICKER"
    manager = StateManager(results_dir=test_dir, run_state_file="test_run_state.json")
    state_filepath = test_dir / f"{ticker}_test_run_state.json"
    invalid_data = {"wrong_key": "some_value"}
    state_filepath.write_text(json.dumps(invalid_data))

    # Act & Assert
    with pytest.raises(ValueError, match="Error loading state file"):
        manager.load_state(ticker)


def test_load_state_with_null_metrics(test_dir: Path) -> None:
    """
    Test that loading a state file with null performance metrics works and
    defaults them to 0.0. This simulates the case of a backtest that
    could not calculate Sharpe/Sortino ratios.
    """
    # Arrange
    ticker = "TEST_TICKER"
    manager = StateManager(results_dir=test_dir, run_state_file="test_run_state.json")
    state_filepath = test_dir / f"{ticker}_test_run_state.json"

    # This is a simplified RunState JSON, focusing on the null metric
    state_with_null_metric = {
        "iteration_number": 1,
        "history": [
            {
                "strategy": {
                    "strategy_name": "Strategy With Null",
                    "indicators": [],
                    "buy_condition": "Close > 0",
                    "sell_condition": "Close < 0",
                },
                "performance": {
                    "sharpe_ratio": None,
                    "sortino_ratio": None,
                    "max_drawdown_pct": -10.5,
                    "annual_return_pct": 5.0,
                },
                "trade_summary": {
                    "total_trades": 0,
                    "win_rate_pct": 0.0,
                    "profit_factor": 0.0,
                    "avg_win_pct": 0.0,
                    "avg_loss_pct": 0.0,
                    "max_consecutive_losses": 0,
                    "avg_trade_duration_bars": 0,
                },
                "is_pruned": False,
            }
        ],
    }
    state_filepath.write_text(json.dumps(state_with_null_metric))

    # Act
    loaded_state = manager.load_state(ticker)

    # Assert
    assert loaded_state is not None
    assert loaded_state.iteration_number == 1
    assert len(loaded_state.history) == 1

    # Crucially, assert that None was parsed correctly
    performance = loaded_state.history[0].performance
    assert performance.sharpe_ratio is None
    assert performance.sortino_ratio is None
    assert performance.max_drawdown_pct == -10.5
    assert performance.annual_return_pct == 5.0
