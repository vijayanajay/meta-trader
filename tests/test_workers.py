import pytest
from pytest import MonkeyPatch
import multiprocessing
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Iterable, Callable

from typer.testing import CliRunner

from praxis_engine import main
from praxis_engine.main import app
from praxis_engine.core.models import (
    BacktestMetrics, Trade, Signal, Config, DataConfig, StrategyParamsConfig,
    FiltersConfig, ScoringConfig, LLMConfig, CostModelConfig, ExitLogicConfig,
    SignalLogicConfig
)

runner = CliRunner()

def test_determine_process_count_auto(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(multiprocessing, "cpu_count", lambda: 8)
    assert main.determine_process_count(["A", "B", "C", "D", "E"], None) == 5
    assert main.determine_process_count([], None) == 1


def test_determine_process_count_config_override(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(multiprocessing, "cpu_count", lambda: 4)
    assert main.determine_process_count(["A", "B", "C"], 2) == 2
    assert main.determine_process_count(["A", "B"], 0) == 1


def test_backtest_cli_trains_model_if_not_exists(monkeypatch: MonkeyPatch) -> None:
    """
    Verify that the `backtest` CLI command attempts to train a model if it
    doesn't exist.
    """
    # Mock that the model file does NOT exist
    monkeypatch.setattr(Path, "exists", lambda self: False)

    # Patch the training function to monitor its calls
    mock_train = MagicMock(return_value=True)
    monkeypatch.setattr("scripts.train_regime_model.train_and_save_model", mock_train)

    # Patch the multiprocessing pool to prevent a real backtest from running
    mock_pool = MagicMock()
    monkeypatch.setattr(multiprocessing, "Pool", mock_pool)

    # Run the CLI command
    result = runner.invoke(app, ["backtest", "--config", "config.ini"])

    # Assert that the training function was called
    assert result.exit_code == 0
    mock_train.assert_called_once()
