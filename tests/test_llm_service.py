import os
import json
import pytest
from unittest.mock import MagicMock, patch

from openai import APIError
from pydantic import ValidationError

from services.llm_service import LLMService
from core.models import (
    PerformanceReport,
    StrategyDefinition,
    TradeSummary,
    Indicator,
)


@pytest.fixture
def mock_openai_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocks the OpenAI client."""
    mock_client_instance = MagicMock()
    mock_constructor = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr("services.llm_service.OpenAI", mock_constructor)
    return mock_client_instance


@pytest.fixture
def llm_service(mock_openai_client: MagicMock) -> LLMService:
    """Provides an LLMService instance with a mocked client."""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "openrouter",
        "OPENROUTER_API_KEY": "dummy_key",
        "OPENROUTER_MODEL": "test-model",
        "OPENROUTER_BASE_URL": "https://dummy.url"
    }):
        with patch("builtins.open", MagicMock()):
            service = LLMService()
    return service


@pytest.fixture
def sample_history() -> list[PerformanceReport]:
    """Provides a sample history of performance reports."""
    from core.models import PerformanceMetrics

    return [
        PerformanceReport(
            strategy=StrategyDefinition(
                strategy_name="SMA_10_20",
                indicators=[
                    Indicator(
                        name="sma10", function="sma", params={"length": 10}
                    )
                ],
                buy_condition="sma10 > close",
                sell_condition="sma10 < close",
            ),
            performance=PerformanceMetrics(
                sharpe_ratio=1.2,
                sortino_ratio=1.8,
                annual_return_pct=15.5,
                max_drawdown_pct=-10.0,
            ),
            trade_summary=TradeSummary(total_trades=10, win_rate_pct=60.0, profit_factor=2.1, avg_win_pct=2.0, avg_loss_pct=-1.5, max_consecutive_losses=2, avg_trade_duration_bars=5),
        )
    ]


def test_get_suggestion_success(
    llm_service: LLMService,
    mock_openai_client: MagicMock,
    sample_history: list[PerformanceReport],
) -> None:
    """
    Tests successful suggestion retrieval and parsing.
    """
    # Arrange
    mock_response_content = {
        "strategy_name": "New_Strategy",
        "indicators": [{"name": "ema50", "function": "ema", "params": {"length": 50}}],
        "buy_condition": "ema50 > close",
        "sell_condition": "ema50 < close",
    }
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = json.dumps(mock_response_content)
    mock_completion.usage.prompt_tokens = 100
    mock_openai_client.chat.completions.create.return_value = mock_completion

    # Act
    result = llm_service.get_suggestion(
        ticker="TEST",
        history=sample_history,
        failed_strategy=None,
        best_strategy_so_far=sample_history[0].strategy
    )

    # Assert
    assert isinstance(result, StrategyDefinition)
    assert result.strategy_name == "New_Strategy"
    mock_openai_client.chat.completions.create.assert_called_once()


def test_get_suggestion_json_decode_error(
    llm_service: LLMService,
    mock_openai_client: MagicMock,
    sample_history: list[PerformanceReport],
) -> None:
    """
    Tests handling of a malformed JSON response from the LLM.
    """
    # Arrange
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This is not valid JSON."
    mock_openai_client.chat.completions.create.return_value = mock_completion

    # Act & Assert
    with pytest.raises(json.JSONDecodeError):
        llm_service.get_suggestion(
            ticker="TEST",
            history=sample_history,
            failed_strategy=None,
            best_strategy_so_far=sample_history[0].strategy
        )


def test_get_suggestion_pydantic_validation_error(
    llm_service: LLMService,
    mock_openai_client: MagicMock,
    sample_history: list[PerformanceReport],
) -> None:
    """
    Tests handling of JSON that doesn't match the Pydantic model.
    """
    # Arrange
    mock_response_content = {"strategy_name": "Invalid_Strategy"}
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = json.dumps(mock_response_content)
    mock_openai_client.chat.completions.create.return_value = mock_completion

    # Act & Assert
    with pytest.raises(ValidationError):
        llm_service.get_suggestion(
            ticker="TEST",
            history=sample_history,
            failed_strategy=None,
            best_strategy_so_far=sample_history[0].strategy
        )


def test_get_suggestion_api_error(
    llm_service: LLMService,
    mock_openai_client: MagicMock,
    sample_history: list[PerformanceReport],
) -> None:
    """
    Tests handling of an APIError from the OpenAI client.
    """
    # Arrange
    mock_openai_client.chat.completions.create.side_effect = APIError("API Error", request=MagicMock(), body=None)

    # Act & Assert
    with pytest.raises(APIError):
        llm_service.get_suggestion(
            ticker="TEST",
            history=sample_history,
            failed_strategy=None,
            best_strategy_so_far=sample_history[0].strategy
        )
