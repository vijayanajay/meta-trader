"""
Unit tests for the LLM Audit Service.
"""
from unittest.mock import MagicMock, patch

import pytest

from praxis_engine.services.llm_audit_service import LLMAuditService


@pytest.fixture
def mock_stats() -> dict[str, float]:
    """A sample dictionary of statistics."""
    return {
        "win_rate": 55.5,
        "profit_factor": 1.8,
        "sample_size": 25,
        "sector_volatility": 15.2,
        "hurst_exponent": 0.45,
    }


@patch.dict(
    "os.environ",
    {
        "OPENROUTER_API_KEY": "test_key",
        "OPENROUTER_BASE_URL": "https://test.com",
        "OPENROUTER_MODEL": "test_model",
    },
)
@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_success(
    mock_openai: MagicMock, mock_stats: dict[str, float]
) -> None:
    """Tests a successful call to get_confidence_score."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "  0.85  "
    mock_openai.return_value.chat.completions.create.return_value = (
        mock_completion
    )

    service = LLMAuditService()
    score = service.get_confidence_score(mock_stats)

    assert score == 0.85
    mock_openai.return_value.chat.completions.create.assert_called_once()
    # You could also assert that the prompt was formatted correctly
    # called_prompt = mock_openai.return_value.chat.completions.create.call_args[1]['messages'][0]['content']
    # assert str(mock_stats['hurst_exponent']) in called_prompt


@patch.dict(
    "os.environ",
    {
        "OPENROUTER_API_KEY": "test_key",
        "OPENROUTER_BASE_URL": "https://test.com",
        "OPENROUTER_MODEL": "test_model",
    },
)
@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_invalid_response(
    mock_openai: MagicMock, mock_stats: dict[str, float]
) -> None:
    """Tests the case where the LLM returns an invalid (non-float) response."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This is not a float"
    mock_openai.return_value.chat.completions.create.return_value = (
        mock_completion
    )

    service = LLMAuditService()
    score = service.get_confidence_score(mock_stats)

    assert score == 0.0


@patch.dict(
    "os.environ",
    {
        "OPENROUTER_API_KEY": "test_key",
        "OPENROUTER_BASE_URL": "https://test.com",
        "OPENROUTER_MODEL": "test_model",
    },
)
@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_api_error(
    mock_openai: MagicMock, mock_stats: dict[str, float]
) -> None:
    """Tests the case where the OpenAI API call raises an exception."""
    mock_openai.return_value.chat.completions.create.side_effect = Exception(
        "API Error"
    )

    service = LLMAuditService()
    score = service.get_confidence_score(mock_stats)

    assert score == 0.0
