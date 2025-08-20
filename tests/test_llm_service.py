import os
import sys
from unittest import mock

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

# Ensure the source code is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from self_improving_quant.services.llm_service import LLMService

# A minimal, reusable mock for the openai.ChatCompletion object
MOCK_COMPLETION = ChatCompletion(
    id="chatcmpl-123",
    choices=[
        Choice(
            finish_reason="stop",
            index=0,
            message=ChatCompletionMessage(content='{"strategy": "mock"}', role="assistant", tool_calls=None),
        )
    ],
    created=1677652288,
    model="mock_model",
    object="chat.completion",
    usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
)

@pytest.mark.parametrize(
    "provider, env_vars, expected_api_key, expected_base_url, expected_model",
    [
        (
            "openai",
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "openai_key", "OPENAI_MODEL": "gpt-4"},
            "openai_key", None, "gpt-4"
        ),
        (
            "openrouter",
            {
                "LLM_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "openrouter_key",
                "OPENROUTER_MODEL": "kimi-2",
                "OPENROUTER_BASE_URL": "https://router.ai/api",
            },
            "openrouter_key", "https://router.ai/api", "kimi-2"
        ),
    ],
)
@mock.patch("self_improving_quant.services.llm_service.load_dotenv")
@mock.patch("self_improving_quant.services.llm_service.openai.OpenAI")
def test_llm_service_initialization(
    mock_openai_client, mock_load_dotenv, provider, env_vars, expected_api_key, expected_base_url, expected_model
):
    """Tests that LLMService initializes the client correctly for each provider."""
    with mock.patch.dict(os.environ, env_vars, clear=True):
        service = LLMService()
        mock_openai_client.assert_called_once_with(api_key=expected_api_key, base_url=expected_base_url)
        assert service.provider == provider
        assert service.model == expected_model

@pytest.mark.parametrize(
    "provider, env_vars, expected_error_msg",
    [
        ("openai", {"LLM_PROVIDER": "openai", "OPENAI_MODEL": "gpt-4"}, "API key for provider 'openai' not found"),
        ("openai", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key"}, "Model for provider 'openai' not found"),
        ("openrouter", {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "key"}, "Model for provider 'openrouter' not found"),
    ]
)
@mock.patch("self_improving_quant.services.llm_service.load_dotenv")
def test_llm_service_missing_env_vars_raises_error(mock_load_dotenv, provider, env_vars, expected_error_msg):
    """Tests that LLMService raises ValueError if required env vars are missing."""
    with mock.patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError) as excinfo:
            LLMService()
        assert expected_error_msg in str(excinfo.value)

@mock.patch("self_improving_quant.services.llm_service.load_dotenv")
@mock.patch("self_improving_quant.services.llm_service.openai.OpenAI")
def test_get_strategy_suggestion_calls_client(mock_openai_client, mock_load_dotenv):
    """Tests the suggestion method calls the client and returns the expected response."""
    mock_instance = mock_openai_client.return_value
    mock_instance.chat.completions.create.return_value = MOCK_COMPLETION

    env_vars = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key", "OPENAI_MODEL": "model"}
    with mock.patch.dict(os.environ, env_vars, clear=True):
        service = LLMService()
        response = service.get_strategy_suggestion(history=[{"some": "history"}])

        mock_instance.chat.completions.create.assert_called_once()
        assert response == '{"strategy": "mock"}'
