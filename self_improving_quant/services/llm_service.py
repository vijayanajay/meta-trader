import os
from typing import Any, Dict, List, Optional

import openai
from dotenv import load_dotenv

__all__ = ["LLMService"]


class LLMService:
    """
    A service to interact with a Large Language Model.
    It can be configured to use either OpenAI or an OpenRouter-compatible API.
    """

    # impure: Loads .env, reads environment variables
    def __init__(self) -> None:
        """Initializes the LLM service client based on environment variables."""
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        api_key: Optional[str]
        base_url: Optional[str] = None
        model: Optional[str]

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")
            model = os.getenv("OPENROUTER_MODEL")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL")
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Must be 'openai' or 'openrouter'.")

        if not api_key:
            raise ValueError(f"API key for provider '{provider}' not found. Set {provider.upper()}_API_KEY.")
        if not model:
            raise ValueError(f"Model for provider '{provider}' not found. Set {provider.upper()}_MODEL.")

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.provider = provider

    # impure: Performs network I/O to an LLM API
    def get_strategy_suggestion(self, history: List[Dict[str, Any]]) -> str:
        """
        Gets a strategy suggestion from the configured LLM.

        Args:
            history: A list of previous reports to provide as context.

        Returns:
            The raw JSON string response from the LLM.
        """
        # In a real implementation, this would load and format a prompt from `prompts/`
        prompt = "Based on the following history, suggest a new trading strategy:\n" + str(history)

        # Per H-28, log cost-related info. Using print as logger isn't available here.
        print(f"INFO: Calling LLM. Provider: {self.provider}, Model: {self.model}")

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a quantitative analyst. Respond with JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        # Per H-28, log token usage.
        if completion.usage:
            print(
                f"INFO: LLM call successful. Tokens: "
                f"Prompt={completion.usage.prompt_tokens}, "
                f"Completion={completion.usage.completion_tokens}"
            )

        response = completion.choices[0].message.content
        if not response:
            # Per H-12, avoid silent failures.
            raise ValueError("LLM returned an empty response.")

        return response
