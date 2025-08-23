"""
Unit tests for the LLM Audit Service.
"""
from pathlib import Path
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


@pytest.fixture
def prompt_template_file(tmp_path: Path) -> Path:
    """Creates a dummy prompt template file."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "test_prompt.txt"
    prompt_file.write_text("Hurst: {{ hurst_exponent }}")
    return prompt_file


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
    mock_openai: MagicMock, mock_stats: dict[str, float], prompt_template_file: Path
) -> None:
    """Tests a successful call to get_confidence_score."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "  0.85  "
    mock_openai.return_value.chat.completions.create.return_value = (
        mock_completion
    )

    service = LLMAuditService(prompt_template_path=str(prompt_template_file))
    score = service.get_confidence_score(mock_stats)

    assert score == 0.85
    mock_openai.return_value.chat.completions.create.assert_called_once()


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
    mock_openai: MagicMock, mock_stats: dict[str, float], prompt_template_file: Path
) -> None:
    """Tests the case where the LLM returns an invalid (non-float) response."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This is not a float"
    mock_openai.return_value.chat.completions.create.return_value = (
        mock_completion
    )

    service = LLMAuditService(prompt_template_path=str(prompt_template_file))
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
    mock_openai: MagicMock, mock_stats: dict[str, float], prompt_template_file: Path
) -> None:
    """Tests the case where the OpenAI API call raises an exception."""
    mock_openai.return_value.chat.completions.create.side_effect = Exception(
        "API Error"
    )

    service = LLMAuditService(prompt_template_path=str(prompt_template_file))
    score = service.get_confidence_score(mock_stats)

    assert score == 0.0
