"""
Tests for the StateManager service.
"""
import json
from pathlib import Path
import pytest
from core.models import RunState, PerformanceReport, StrategyDefinition, TradeSummary
from services.state_manager import StateManager


@pytest.fixture
def test_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory for test files.
    """
    return tmp_path


@pytest.fixture
def state_filepath(test_dir: Path) -> Path:
    """
    Get the path to a test state file.
    """
    return test_dir / "test_run_state.json"


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
        sharpe_ratio=1.2,
        sortino_ratio=1.8,
        max_drawdown_pct=-15.0,
        annual_return_pct=25.0,
        trade_summary=trade_summary,
    )
    return RunState(iteration_number=1, history=[report])


def test_save_and_load_state(
    state_filepath: Path, sample_run_state: RunState
) -> None:
    """
    Test that the StateManager can save a RunState and load it back correctly.
    """
    # Arrange
    manager = StateManager(state_filepath)

    # Act
    manager.save_state(sample_run_state)
    loaded_state = manager.load_state()

    # Assert
    assert state_filepath.exists()
    assert loaded_state == sample_run_state
    assert loaded_state.iteration_number == 1
    assert len(loaded_state.history) == 1
    assert loaded_state.history[0].sharpe_ratio == 1.2


def test_load_state_non_existent_file(state_filepath: Path) -> None:
    """
    Test that loading a non-existent state file returns a default RunState.
    """
    # Arrange
    manager = StateManager(state_filepath)

    # Act
    loaded_state = manager.load_state()

    # Assert
    assert not state_filepath.exists()
    assert isinstance(loaded_state, RunState)
    assert loaded_state.iteration_number == 0
    assert len(loaded_state.history) == 0


def test_load_state_corrupted_file(state_filepath: Path) -> None:
    """
    Test that loading a corrupted JSON file raises a ValueError.
    """
    # Arrange
    state_filepath.write_text("this is not valid json")
    manager = StateManager(state_filepath)

    # Act & Assert
    with pytest.raises(ValueError, match="Error decoding state file"):
        manager.load_state()


def test_load_state_invalid_schema(state_filepath: Path) -> None:
    """
    Test that loading a file with a different schema raises a ValueError.
    """
    # Arrange
    invalid_data = {"wrong_key": "some_value"}
    state_filepath.write_text(json.dumps(invalid_data))
    manager = StateManager(state_filepath)

    # Act & Assert
    with pytest.raises(ValueError, match="Error loading state file"):
        manager.load_state()
