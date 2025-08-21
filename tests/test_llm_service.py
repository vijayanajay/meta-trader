import os
from unittest.mock import MagicMock, patch

import pytest

import openai

from self_improving_quant.core.models import IterationReport, StrategyDefinition
from self_improving_quant.services.llm_service import LLMService


@pytest.fixture
def mock_llm_service() -> LLMService:
    """Fixture to create a mocked LLMService instance."""
    mock_env = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key", "OPENAI_MODEL": "model"}
    with patch.dict(os.environ, mock_env, clear=True), patch(
        "pathlib.Path.read_text", return_value="Prompt: {history}"
    ), patch("self_improving_quant.services.llm_service.openai.OpenAI") as mock_openai_client:
        mock_llm_instance = mock_openai_client.return_value
        mock_usage = MagicMock()
        mock_usage.total_tokens = 123
        mock_llm_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"a": 1}'))], usage=mock_usage
        )
        service = LLMService()
        service.client = mock_llm_instance  # Inject mock client
        yield service


def create_mock_report(iteration: int) -> IterationReport:
    """Helper to create a mock iteration report with all required fields."""
    strategy = StrategyDefinition(rationale=f"test_{iteration}", indicators=[], buy_signal="b", sell_signal="s")
    # Use aliases for keys as expected by the Pydantic model
    report_data = {
        "iteration": iteration,
        "status": "success",
        "strategy": strategy,
        "edge_score": 0.1,
        "Start": "2022-01-01",
        "End": "2023-01-01",
        "Duration": "365 days",
        "Exposure Time [%]": 50.0,
        "Equity Final [$]": 110000.0,
        "Equity Peak [$]": 115000.0,
        "Return [%]": 10.0,
        "Buy & Hold Return [%]": 5.0,
        "Return (Ann.) [%]": 10.0,
        "Volatility (Ann.) [%]": 15.0,
        "Sharpe Ratio": 1.5,
        "Sortino Ratio": 2.0,
        "Calmar Ratio": 0.5,
        "Max. Drawdown [%]": -5.0,
        "Avg. Drawdown [%]": -2.5,
        "Max. Drawdown Duration": 30,
        "Avg. Drawdown Duration": 15,
        "# Trades": 20,
        "Win Rate [%]": 60.0,
        "Best Trade [%]": 5.0,
        "Worst Trade [%]": -3.0,
        "Avg. Trade [%]": 1.0,
        "Max. Trade Duration": 10,
        "Avg. Trade Duration": 5,
        "Profit Factor": 1.5,
        "Expectancy [%]": 1.0,
        "SQN": 1.5,
    }
    return IterationReport.model_validate(report_data)


def test_format_history(mock_llm_service: LLMService) -> None:
    """Tests the _format_history method."""
    reports = [create_mock_report(i) for i in range(3)]

    formatted_str = mock_llm_service._format_history(reports)

    assert '"iteration": 0' in formatted_str
    assert '"iteration": 1' in formatted_str
    assert '"iteration": 2' in formatted_str
    assert '"edge_score": "0.1000"' in formatted_str


def test_get_strategy_suggestion_formats_prompt(mock_llm_service: LLMService) -> None:
    """Tests that the LLM service correctly formats the prompt."""
    mock_llm_service.get_strategy_suggestion(history=[])  # History formatting is tested above

    args, kwargs = mock_llm_service.client.chat.completions.create.call_args
    user_prompt = kwargs["messages"][0]["content"]
    assert user_prompt.startswith("Prompt:")
    assert "No history available" in user_prompt


@patch("time.sleep", return_value=None)
def test_get_strategy_suggestion_with_retry(mock_sleep: MagicMock, mock_llm_service: LLMService) -> None:
    """Tests that get_strategy_suggestion retries on API errors."""
    mock_create = mock_llm_service.client.chat.completions.create
    mock_create.side_effect = [
        openai.APITimeoutError(request=MagicMock()),
        mock_create.return_value,  # Success on the second call
    ]

    response = mock_llm_service.get_strategy_suggestion(history=[])

    assert response == '{"a": 1}'
    assert mock_create.call_count == 2
    mock_sleep.assert_called_once()


def test_configurable_history_length(monkeypatch) -> None:
    """Tests that LLM_MAX_HISTORY_ENTRIES configures history length."""
    monkeypatch.setenv("LLM_MAX_HISTORY_ENTRIES", "2")
    reports = [create_mock_report(i) for i in range(5)]  # Create 5 reports

    # Re-initialize service to pick up the new env var
    service = LLMService()
    formatted_str = service._format_history(reports)

    assert '"iteration": 0' not in formatted_str
    assert '"iteration": 1' not in formatted_str
    assert '"iteration": 2' not in formatted_str
    assert '"iteration": 3' in formatted_str
    assert '"iteration": 4' in formatted_str
