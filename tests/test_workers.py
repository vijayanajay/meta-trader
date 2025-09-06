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
