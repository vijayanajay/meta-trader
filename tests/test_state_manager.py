import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from self_improving_quant.core.models import IterationReport, StrategyDefinition
from self_improving_quant.services.state_manager import load_state, save_state

def test_save_and_load_state(tmp_path: Path) -> None:
    """Tests that state can be saved and loaded correctly."""
    # Arrange
    file_path = tmp_path / "run_state.json"
    strategy = StrategyDefinition(rationale="test", indicators=[], buy_signal="b", sell_signal="s")
    report_data = {
        "iteration": 0, "strategy": strategy.model_dump(), "edge_score": 0.1, "Return [%]": 10,
        "Max. Drawdown [%]": -5, "Sharpe Ratio": 1.5, "Win Rate [%]": 60,
        "Start": "2022-01-01", "End": "2023-01-01", "Duration": "365 days",
        "Exposure Time [%]": 50, "Equity Final [$]": 110000, "Equity Peak [$]": 115000,
        "Buy & Hold Return [%]": 5.0, "Return (Ann.) [%]": 10.0,
        "Volatility (Ann.) [%]": 15.0, "Sortino Ratio": 2.0, "Calmar Ratio": 0.5,
        "Avg. Drawdown [%]": -2.5, "Max. Drawdown Duration": 30, "Avg. Drawdown Duration": 15,
        "# Trades": 20, "Best Trade [%]": 5.0, "Worst Trade [%]": -3.0, "Avg. Trade [%]": 1.0,
        "Max. Trade Duration": 10, "Avg. Trade Duration": 5, "Profit Factor": 1.5,
        "Expectancy [%]": 1.0, "SQN": 1.5
    }
    history = [IterationReport.model_validate(report_data)]

    # Act
    save_state(history, file_path)
    loaded_history = load_state(file_path)

    # Assert
    assert len(loaded_history) == 1
    assert loaded_history[0].iteration == 0
    assert loaded_history[0].edge_score == pytest.approx(0.1)
    assert loaded_history[0].strategy.rationale == "test"

def test_load_state_non_existent_file(tmp_path: Path) -> None:
    """Tests that loading a non-existent state file returns an empty list."""
    history = load_state(tmp_path / "non_existent.json")
    assert history == []

def test_load_state_corrupted_file(tmp_path: Path) -> None:
    """Tests that loading a corrupted state file returns an empty list."""
    file_path = tmp_path / "corrupted.json"
    file_path.write_text("this is not json")
    history = load_state(file_path)
    assert history == []
