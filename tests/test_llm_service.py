import os
from unittest.mock import MagicMock, patch

import pytest

from self_improving_quant.core.models import IterationReport, StrategyDefinition
from self_improving_quant.services.llm_service import LLMService, _format_history


def test_format_history() -> None:
    """Tests the _format_history function."""
    strategy = StrategyDefinition(rationale="test", indicators=[], buy_signal="b", sell_signal="s")
    report_data = {
        "iteration": 0, "strategy": strategy, "edge_score": 0.1, "Return [%]": 10,
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
    # Pydantic model is populated by alias, so we create it from a dict
    reports = [IterationReport.model_validate(report_data)]

    # Act
    formatted_str = _format_history(reports)

    # Assert
    assert '"iteration": 0' in formatted_str
    assert '"edge_score": "0.1000"' in formatted_str
    assert '"return_pct": "10.00%"' in formatted_str

@patch("self_improving_quant.services.llm_service.openai.OpenAI")
@patch("pathlib.Path.read_text", return_value="Prompt: {history}")
def test_get_strategy_suggestion_formats_prompt(mock_read_text: MagicMock, mock_openai_client: MagicMock) -> None:
    """Tests that the LLM service correctly formats the prompt."""
    mock_env = {
        "LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key", "OPENAI_MODEL": "model"
    }
    mock_llm_instance = mock_openai_client.return_value
    mock_usage = MagicMock()
    mock_usage.total_tokens = 123
    mock_llm_instance.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"a": 1}'))],
        usage=mock_usage
    )

    with patch.dict(os.environ, mock_env, clear=True):
        service = LLMService()

    # Act
    service.get_strategy_suggestion(history=[]) # History formatting is tested above

    # Assert
    mock_read_text.assert_called_once()
    args, kwargs = mock_llm_instance.chat.completions.create.call_args
    user_prompt = kwargs["messages"][0]["content"]
    assert user_prompt.startswith("Prompt:")
    assert "No history available" in user_prompt
