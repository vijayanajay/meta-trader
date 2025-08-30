"""
Unit tests for the LLMAuditService.
"""
import pytest
from unittest.mock import patch, MagicMock, create_autospec
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Generator
import httpx
from _pytest.logging import LogCaptureFixture


from openai import APIConnectionError, RateLimitError, AuthenticationError
from praxis_engine.services.llm_audit_service import LLMAuditService
from praxis_engine.core.models import Signal, LLMConfig

PROMPT_TEMPLATE = """
You are a quantitative analyst AI. Your task is to provide a confidence score.
Your response must be a single floating-point number between 0.0 and 1.0.
- Historical Win Rate (>1.77% net return in 20 days): {{ win_rate }}%
- Historical Profit Factor: {{ profit_factor }}
- Historical Sample Size (number of past signals): {{ sample_size }}
- Current Sector Volatility (annualized): {{ sector_volatility }}%
- Current Hurst Exponent: {{ hurst_exponent }}
"""

@pytest.fixture(scope="module")
def prompt_path() -> Path:
    """Fixture for the prompt template path, created once per module."""
    path = Path(__file__).parent / "test_prompt.txt"
    path.write_text(PROMPT_TEMPLATE)
    return path

@pytest.fixture
def llm_config(prompt_path: Path) -> LLMConfig:
    """Fixture for LLM configuration."""
    return LLMConfig(
        provider="test",
        model="test-model",
        prompt_template_path=str(prompt_path),
        confidence_threshold=0.7,
        min_composite_score_for_llm=0.05,
    )

@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Creates a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
    data = {"Close": np.random.uniform(95, 105, 100)}
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def llm_audit_service(
    llm_config: LLMConfig,
) -> Generator[LLMAuditService, None, None]:
    """Fixture for an initialized LLMAuditService with a mocked OpenAI client."""
    with patch("praxis_engine.services.llm_audit_service.OpenAI") as mock_openai:
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "test-key",
                "OPENROUTER_BASE_URL": "https://test.com",
                "OPENROUTER_MODEL": "test-model",
            },
            clear=True
        ):
            service = LLMAuditService(config=llm_config)
            # Attach mock to instance for easy access in tests
            service.mock_openai_client = mock_openai.return_value # type: ignore
            yield service

class TestLLMAuditServiceInitialization:
    """Tests for the initialization logic of the LLM Audit Service."""

    def test_initialization_with_openrouter(self, llm_config: LLMConfig) -> None:
        """Test successful initialization with OpenRouter provider."""
        with patch("praxis_engine.services.llm_audit_service.OpenAI") as mock_openai:
            with patch.dict(
                "os.environ",
                {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "or-key", "OPENROUTER_BASE_URL": "or_url"},
                clear=True
            ):
                service = LLMAuditService(config=llm_config)
                assert service.client is not None
                mock_openai.assert_called_once_with(base_url="or_url", api_key="or-key", timeout=30.0)

    def test_initialization_with_openai(self, llm_config: LLMConfig) -> None:
        """Test successful initialization with OpenAI provider."""
        with patch("praxis_engine.services.llm_audit_service.OpenAI") as mock_openai:
            with patch.dict(
                "os.environ",
                {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "oa-key"},
                clear=True
            ):
                service = LLMAuditService(config=llm_config)
                assert service.client is not None
                mock_openai.assert_called_once_with(base_url=None, api_key="oa-key", timeout=30.0)

    @pytest.mark.parametrize("provider", ["openrouter", "openai"])
    def test_initialization_fails_with_missing_key(
        self, llm_config: LLMConfig, caplog: LogCaptureFixture, provider: str
    ) -> None:
        """Test that initialization fails if the API key is missing."""
        with patch.dict("os.environ", {"LLM_PROVIDER": provider, f"{provider.upper()}_API_KEY": ""}, clear=True):
            service = LLMAuditService(config=llm_config)
            assert service.client is None
            assert f"API key for {provider} not found" in caplog.text
            # Verify it returns the safe default score (0.0)
            assert service.get_confidence_score(MagicMock(), MagicMock(), MagicMock()) == 0.0
            assert "LLM client not initialized" in caplog.text

    def test_initialization_fails_with_unsupported_provider(
        self, llm_config: LLMConfig, caplog: LogCaptureFixture
    ) -> None:
        """Test that initialization fails for an unsupported provider."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "unsupported"}, clear=True):
            service = LLMAuditService(config=llm_config)
            assert service.client is None
            assert "LLM_PROVIDER 'unsupported' is not supported" in caplog.text

class TestParseLLMResponse:
    """Tests for the _parse_llm_response helper method."""
    @pytest.mark.parametrize("response, expected", [
        ("0.75", 0.75),
        ("Confidence: 0.8", 0.8),
        ("Invalid response", 0.0),
        (None, 0.0),
        ("", 0.0),
        ("1.5", 1.0), # Clamps above 1.0
        ("-0.5", 0.0), # Clamps below 0.0
        ("Here is a score: 0.95, what do you think?", 0.95)
    ])
    def test_parsing_scenarios(self, llm_audit_service: LLMAuditService, response: str, expected: float) -> None:
        assert llm_audit_service._parse_llm_response(response) == expected

class TestGetConfidenceScore:
    """Tests for the main get_confidence_score method."""
    def test_success_case(self, llm_audit_service: LLMAuditService, sample_dataframe: pd.DataFrame) -> None:
        mock_client = llm_audit_service.mock_openai_client # type: ignore
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "0.85"
        mock_client.chat.completions.create.return_value = mock_completion
        stats = {"win_rate": 60.0, "profit_factor": 2.5, "sample_size": 10}
        signal = Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["d"], sector_vol=15.5)

        score = llm_audit_service.get_confidence_score(stats, signal, sample_dataframe)

        assert score == 0.85
        prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "60.0" in prompt and "2.50" in prompt and "15.5" in prompt

    @pytest.mark.parametrize("error_class, provider, expected_log", [
        (APIConnectionError(request=MagicMock()), "openrouter", "LLM API Error: APIConnectionError"),
        (RateLimitError("limit reached", response=httpx.Response(429, request=MagicMock()), body=None), "openrouter", "LLM API Error: RateLimitError"),
        (AuthenticationError("auth error", response=httpx.Response(401, request=MagicMock()), body=None), "openrouter", "OpenRouter API key error"),
        (AuthenticationError("auth error", response=httpx.Response(401, request=MagicMock()), body=None), "openai", "LLM API Authentication Error"),
        (Exception("Generic Error"), "openrouter", "An unexpected error in get_confidence_score"),
    ])
    def test_specific_api_errors_return_zero(
        self,
        llm_audit_service: LLMAuditService,
        sample_dataframe: pd.DataFrame,
        caplog: LogCaptureFixture,
        error_class: Exception,
        provider: str,
        expected_log: str,
    ) -> None:
        llm_audit_service.llm_provider = provider
        llm_audit_service.mock_openai_client.chat.completions.create.side_effect = error_class # type: ignore

        score = llm_audit_service.get_confidence_score(
            {}, MagicMock(spec=Signal, sector_vol=15.0), sample_dataframe
        )

        assert score == 0.0
        assert expected_log in caplog.text

    def test_hurst_calculation_fails(
        self,
        llm_audit_service: LLMAuditService,
        sample_dataframe: pd.DataFrame,
        caplog: LogCaptureFixture,
    ) -> None:
        with patch("praxis_engine.services.llm_audit_service.hurst_exponent", return_value=None):
            score = llm_audit_service.get_confidence_score(
                {}, MagicMock(spec=Signal, sector_vol=15.0), sample_dataframe
            )
            assert score == 0.0
            assert "Could not calculate Hurst exponent" in caplog.text

    def test_template_not_found(
        self,
        llm_config: LLMConfig,
        sample_dataframe: pd.DataFrame,
        caplog: LogCaptureFixture,
    ) -> None:
        llm_config.prompt_template_path = "/non/existent/path/prompt.txt"
        with patch("praxis_engine.services.llm_audit_service.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "key"}, clear=True):
            service = LLMAuditService(config=llm_config)
            score = service.get_confidence_score({}, MagicMock(spec=Signal, sector_vol=15.0), sample_dataframe)
            assert score == 0.0
            assert "Prompt template not found" in caplog.text
