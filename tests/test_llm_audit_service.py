"""
Unit tests for the LLMAuditService.
"""
import pytest
from unittest.mock import patch, MagicMock, create_autospec
import pandas as pd
import os
import numpy as np
from pathlib import Path
import itertools
from typing import Generator

from praxis_engine.services.llm_audit_service import LLMAuditService
from praxis_engine.services.signal_engine import SignalEngine
from praxis_engine.services.validation_service import ValidationService
from praxis_engine.services.execution_simulator import ExecutionSimulator
from praxis_engine.core.models import (
    Signal,
    ValidationScores,
    LLMConfig,
    StrategyParamsConfig,
)

PROMPT_TEMPLATE = """
You are a quantitative analyst AI. Your task is to provide a confidence score on a potential mean-reversion trade signal based on its historical performance characteristics.

**Do not provide any explanation or commentary. Your response must be a single floating-point number between 0.0 and 1.0.**

Here are the statistics for the signal on a given stock:
- Historical Win Rate (>1.77% net return in 20 days): {{ win_rate }}%
- Historical Profit Factor: {{ profit_factor }}
- Historical Sample Size (number of past signals): {{ sample_size }}
- Current Sector Volatility (annualized): {{ sector_volatility }}%
- Current Hurst Exponent: {{ hurst_exponent }}

Based on these statistics, what is the confidence that this signal is not a statistical anomaly and is likely to be a profitable trade?

Confidence Score:
"""


@pytest.fixture
def llm_config() -> LLMConfig:
    """Fixture for LLM configuration."""
    prompt_path = Path(__file__).parent / "test_prompt.txt"
    prompt_path.write_text(PROMPT_TEMPLATE)
    return LLMConfig(
        provider="openrouter",
        model="test-model",
        prompt_template_path=str(prompt_path),
        confidence_threshold=0.7,
        min_composite_score_for_llm=0.5,
    )


@pytest.fixture
def strategy_params() -> StrategyParamsConfig:
    """Fixture for strategy parameters."""
    return StrategyParamsConfig(
        min_history_days=50,
        exit_days=10,
        bb_length=20,
        bb_std=2.0,
        rsi_length=14,
        hurst_length=100,
        liquidity_lookback_days=5,
    )


@pytest.fixture
def mock_signal_engine(strategy_params: StrategyParamsConfig) -> MagicMock:
    """Fixture for a mocked SignalEngine."""
    mock = create_autospec(SignalEngine, instance=True)
    mock.params = strategy_params
    return mock # type: ignore [no-any-return]


@pytest.fixture
def mock_validation_service() -> MagicMock:
    """Fixture for a mocked ValidationService."""
    return create_autospec(ValidationService, instance=True) # type: ignore [no-any-return]


@pytest.fixture
def mock_execution_simulator() -> MagicMock:
    """Fixture for a mocked ExecutionSimulator."""
    return create_autospec(ExecutionSimulator, instance=True) # type: ignore [no-any-return]


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Creates a sample dataframe for testing historical performance."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
    data = {
        "Open": np.random.uniform(95, 105, 100),
        "Close": np.random.uniform(95, 105, 100),
        "High": np.random.uniform(105, 110, 100),
        "Low": np.random.uniform(90, 95, 100),
        "Volume": np.random.uniform(1e6, 5e6, 100),
        "sector_vol": np.random.uniform(15, 25, 100),
    }
    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def llm_audit_service(
    llm_config: LLMConfig,
) -> Generator[LLMAuditService, None, None]:
    """Fixture for an initialized LLMAuditService with a mocked OpenAI client."""
    with patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_BASE_URL": "https://test.com",
        },
        clear=True,
    ):
        # We need to reload the config for it to pick up the mocked env vars
        llm_config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        llm_config.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL")

        with patch("praxis_engine.services.llm_audit_service.OpenAI") as mock_openai:
            service = LLMAuditService(config=llm_config)
            service.mock_openai_client = mock_openai.return_value  # type: ignore
            yield service


class TestParseLLMResponse:
    def test_parse_valid_float(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response("0.75") == 0.75

    def test_parse_float_with_text(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response("Confidence: 0.8") == 0.8

    def test_parse_invalid_text(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response("Invalid response") == 0.0

    def test_parse_empty_response(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response(None) == 0.0
        assert llm_audit_service._parse_llm_response("") == 0.0

    def test_clamps_above_one(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response("1.5") == 1.0

    def test_clamps_below_zero(self, llm_audit_service: LLMAuditService) -> None:
        assert llm_audit_service._parse_llm_response("-0.5") == 0.0


class TestGetConfidenceScore:
    def test_success_case(
        self, llm_audit_service: LLMAuditService, sample_dataframe: pd.DataFrame
    ) -> None:
        # Arrange
        mock_client = llm_audit_service.mock_openai_client # type: ignore
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "0.85"
        mock_client.chat.completions.create.return_value = mock_completion

        historical_stats = {"win_rate": 60.0, "profit_factor": 2.5, "sample_size": 10}

        # Act
        score = llm_audit_service.get_confidence_score(
            historical_stats=historical_stats,
            df_window=sample_dataframe,
            signal=Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["d"], sector_vol=15),
        )
        # Assert
        assert score == 0.85
        prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "60.0" in prompt
        assert "2.50" in prompt

    def test_api_error_returns_zero(
        self, llm_audit_service: LLMAuditService, sample_dataframe: pd.DataFrame
    ) -> None:
        # Arrange
        mock_client = llm_audit_service.mock_openai_client # type: ignore
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        # Act
        score = llm_audit_service.get_confidence_score(
            historical_stats={},
            df_window=sample_dataframe,
            signal=Signal(entry_price=100, stop_loss=98, exit_target_days=10, frames_aligned=["d"], sector_vol=15),
        )
        # Assert
        assert score == 0.0
