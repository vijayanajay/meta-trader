"""
Unit tests for the LLMAuditService.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path

from praxis_engine.services.llm_audit_service import LLMAuditService
from praxis_engine.core.models import Signal, ValidationResult, LLMConfig

@pytest.fixture
def llm_config() -> LLMConfig:
    """Fixture for LLM configuration."""
    return LLMConfig(
        model="test-model",
        prompt_template_path=str(Path(__file__).parent / "test_prompt.txt"),
        confidence_threshold=0.7,
    )

@pytest.fixture
def sample_signal() -> Signal:
    """A sample signal for testing."""
    return Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["daily"], sector_vol=15.0)

@pytest.fixture
def sample_validation() -> ValidationResult:
    """A sample validation result for testing."""
    return ValidationResult(is_valid=True)

@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_success(
    mock_openai: MagicMock, llm_config: LLMConfig, sample_signal: Signal, sample_validation: ValidationResult
) -> None:
    """Tests a successful call to get_confidence_score."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "  0.85  "
    mock_openai.return_value.chat.completions.create.return_value = mock_completion

    service = LLMAuditService(config=llm_config)

    # Create a dummy dataframe
    df = pd.DataFrame({'Close': [100.0]})

    score = service.get_confidence_score(df, sample_signal, sample_validation)

    assert score == 0.85
    mock_openai.return_value.chat.completions.create.assert_called_once()

@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_invalid_response(
    mock_openai: MagicMock, llm_config: LLMConfig, sample_signal: Signal, sample_validation: ValidationResult
) -> None:
    """Tests the case where the LLM returns an invalid (non-float) response."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "This is not a float"
    mock_openai.return_value.chat.completions.create.return_value = mock_completion

    service = LLMAuditService(config=llm_config)
    df = pd.DataFrame({'Close': [100.0]})
    score = service.get_confidence_score(df, sample_signal, sample_validation)

    assert score == 0.0

@patch("praxis_engine.services.llm_audit_service.OpenAI")
def test_get_confidence_score_api_error(
    mock_openai: MagicMock, llm_config: LLMConfig, sample_signal: Signal, sample_validation: ValidationResult
) -> None:
    """Tests the case where the OpenAI API call raises an exception."""
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

    service = LLMAuditService(config=llm_config)
    df = pd.DataFrame({'Close': [100.0]})
    score = service.get_confidence_score(df, sample_signal, sample_validation)

    assert score == 0.0
