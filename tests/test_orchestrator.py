#
# test_orchestrator.py
#
"""
Unit and integration tests for the Orchestrator.
"""
import pytest
from unittest.mock import MagicMock, call

from orchestrator import Orchestrator
from core.models import RunState, PerformanceReport, StrategyDefinition, PerformanceMetrics, TradeSummary


def create_mock_report(sharpe: float, is_pruned: bool = False) -> MagicMock:
    """Helper to create a mock PerformanceReport with nested attributes."""
    perf_metrics = MagicMock(spec=PerformanceMetrics)
    perf_metrics.sharpe_ratio = sharpe

    report = MagicMock(spec=PerformanceReport)
    report.is_pruned = is_pruned
    report.performance = perf_metrics
    report.strategy = MagicMock(spec=StrategyDefinition)
    report.strategy.strategy_name = "Mock Strategy"
    report.next_strategy_suggestion = MagicMock(spec=StrategyDefinition)
    report.next_strategy_suggestion.strategy_name = "Next Mock Strategy"

    return report


@pytest.fixture
def mock_services() -> dict[str, MagicMock]:
    """
    Provides a dictionary of mocked services for injection into the Orchestrator.
    """
    config_service = MagicMock()
    state_manager = MagicMock()
    data_service = MagicMock()
    strategy_engine = MagicMock()
    backtester = MagicMock()
    report_generator = MagicMock()
    llm_service = MagicMock()

    mock_config = MagicMock()
    mock_config.app.tickers = ["TEST.NS"]
    mock_config.app.iterations = 2
    mock_config.app.sharpe_threshold = 0.1
    config_service.load_config.return_value = mock_config

    data_service.get_data.return_value = (MagicMock(), MagicMock())
    backtester.run.return_value = (MagicMock(), MagicMock())
    llm_service.get_suggestion.return_value = MagicMock(spec=StrategyDefinition)

    return {
        "config_service": config_service,
        "state_manager": state_manager,
        "data_service": data_service,
        "strategy_engine": strategy_engine,
        "backtester": backtester,
        "report_generator": report_generator,
        "llm_service": llm_service,
    }


def test_orchestrator_run_from_scratch(mock_services: dict[str, MagicMock]) -> None:
    """
    Tests a successful run from scratch with no pre-existing state.
    """
    mock_services["state_manager"].load_state.return_value = RunState(iteration_number=0, history=[])
    mock_services["report_generator"].generate.return_value = create_mock_report(sharpe=1.5)

    orchestrator = Orchestrator(**mock_services)
    orchestrator.run()

    assert mock_services["backtester"].run.call_count == 2
    assert mock_services["report_generator"].generate.call_count == 2
    assert mock_services["llm_service"].get_suggestion.call_count == 1
    assert mock_services["state_manager"].save_state.call_count == 2


def test_orchestrator_resumes_from_existing_state(mock_services: dict[str, MagicMock]) -> None:
    """
    Tests that the orchestrator correctly resumes from a previously saved state.
    """
    # Fix: The report in history MUST have a next_strategy_suggestion
    existing_report = create_mock_report(sharpe=1.2)
    existing_state = RunState(iteration_number=1, history=[existing_report])
    mock_services["state_manager"].load_state.return_value = existing_state

    # The new report generated for iteration 1
    mock_services["report_generator"].generate.return_value = create_mock_report(sharpe=1.8)

    orchestrator = Orchestrator(**mock_services)
    orchestrator.run()

    mock_services["backtester"].run.assert_called_once()
    mock_services["report_generator"].generate.assert_called_once()
    # LLM not called because loop finishes after this iteration (1 of 2)
    mock_services["llm_service"].get_suggestion.assert_not_called()
    mock_services["state_manager"].save_state.assert_called_once()


def test_orchestrator_prunes_bad_strategy(mock_services: dict[str, MagicMock]) -> None:
    """
    Tests the pruning logic for a strategy with a low Sharpe ratio.
    """
    # Fix: The report in history MUST have a next_strategy_suggestion
    prev_report = create_mock_report(sharpe=1.2)
    mock_services["state_manager"].load_state.return_value = RunState(iteration_number=1, history=[prev_report])
    mock_services["config_service"].load_config.return_value.app.iterations = 3 # Fix: Run more iterations

    # This is the report for the current, failing iteration
    bad_report = create_mock_report(sharpe=-0.5)
    mock_services["report_generator"].generate.return_value = bad_report

    orchestrator = Orchestrator(**mock_services)
    orchestrator.run()

    # The report object itself is modified in place
    assert bad_report.is_pruned is True
    # LLM is still called, but with failure context
    mock_services["llm_service"].get_suggestion.assert_called_once()
    _, call_kwargs = mock_services["llm_service"].get_suggestion.call_args
    assert call_kwargs["failed_strategy"] is bad_report


def test_orchestrator_handles_backtest_failure(mock_services: dict[str, MagicMock], monkeypatch) -> None:
    """
    Tests that the orchestrator handles an exception during a backtest.
    """
    # Fix: The report in history MUST have a next_strategy_suggestion
    prev_report = create_mock_report(sharpe=1.2)
    mock_services["state_manager"].load_state.return_value = RunState(iteration_number=1, history=[prev_report])
    mock_services["config_service"].load_config.return_value.app.iterations = 3 # Fix: Run more iterations
    mock_services["backtester"].run.side_effect = ValueError("Test Exception")

    failure_report = create_mock_report(sharpe=-999, is_pruned=True)
    # The orchestrator calls the class method, so we patch it on the class
    monkeypatch.setattr(PerformanceReport, "create_pruned", MagicMock(return_value=failure_report))

    orchestrator = Orchestrator(**mock_services)
    orchestrator.run()

    PerformanceReport.create_pruned.assert_called_once()
    mock_services["state_manager"].save_state.assert_called_once()
    saved_state = mock_services["state_manager"].save_state.call_args[0][1]
    assert saved_state.history[-1] is failure_report
    # LLM is still called, but with the failure report as context
    _, call_kwargs = mock_services["llm_service"].get_suggestion.call_args
    assert call_kwargs["failed_strategy"] is failure_report
