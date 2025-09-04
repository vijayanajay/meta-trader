import pytest
from pytest import MonkeyPatch
import multiprocessing

from praxis_engine import main


class DummyConfig:
    pass


def test_determine_process_count_auto(monkeypatch: MonkeyPatch) -> None:
    # Simulate 8 CPU cores
    monkeypatch.setattr(multiprocessing, "cpu_count", lambda: 8)

    # 5 stocks -> should pick min(5,8) == 5
    processes = main.determine_process_count(["A", "B", "C", "D", "E"], None)
    assert processes == 5

    # 0 stocks -> should pick 1
    processes = main.determine_process_count([], None)
    assert processes == 1


def test_determine_process_count_config_override(monkeypatch: MonkeyPatch) -> None:
    # Simulate 4 CPU cores
    monkeypatch.setattr(multiprocessing, "cpu_count", lambda: 4)

    # cfg_workers specified as 2 -> should use 2
    processes = main.determine_process_count(["A", "B", "C"], 2)
    assert processes == 2

    # cfg_workers specified as 0 -> clamped to 1
    processes = main.determine_process_count(["A", "B"], 0)
    assert processes == 1

    # cfg_workers specified as an int
    processes = main.determine_process_count(["A"], 3)
    assert processes == 3


def test_determine_process_count_respects_cpu(monkeypatch: MonkeyPatch) -> None:
    # Simulate 2 CPU cores
    monkeypatch.setattr(multiprocessing, "cpu_count", lambda: 2)

    # More stocks than CPU cores -> should not exceed cpu_cores when cfg_workers is None
    processes = main.determine_process_count(["A", "B", "C", "D"], None)
    assert processes == 2
