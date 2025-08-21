import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

from self_improving_quant.core.models import IterationReport

__all__ = ["LLMService"]

logger = logging.getLogger(__name__)
LOGS_DIR = Path("logs")
AUDIT_LOG_FILE = LOGS_DIR / "llm_audit.jsonl"


def _format_history(history: list[IterationReport], max_entries: int = 5) -> str:
    """Formats the last N iteration reports into a string for the LLM prompt."""
    if not history:
        return "No history available. This is the first iteration."

    recent_history = history[-max_entries:]
    formatted_entries = []
    for report in recent_history:
        entry = {
            "iteration": report.iteration,
            "status": report.status,
            "error_message": report.error_message,
            "strategy": report.strategy.model_dump(),
            "performance": {
                "edge_score": f"{report.edge_score:.4f}" if report.edge_score is not None else "N/A",
                "return_pct": f"{report.return_pct:.2f}%",
                "max_drawdown_pct": f"{report.max_drawdown_pct:.2f}%",
                "sharpe_ratio": f"{report.sharpe_ratio:.2f}",
                "win_rate_pct": f"{report.win_rate_pct:.2f}%",
            },
        }
        formatted_entries.append(json.dumps(entry, indent=2))

    return "\n\n---\n\n".join(formatted_entries)


class LLMService:
    """
    A service to interact with a Large Language Model.
    It can be configured to use either OpenAI or an OpenRouter-compatible API.
    """

    # impure: Loads .env, reads environment variables, reads prompt file
    def __init__(self, prompt_path: Path | str = "self_improving_quant/prompts/quant_analyst.txt") -> None:
        """Initializes the LLM service client based on environment variables."""
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        api_key: str | None
        base_url: str | None = None
        model: str | None

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
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
        self.prompt_version = "1.0"  # Hardcoded for now, could be part of prompt filename
        try:
            self.base_prompt = Path(prompt_path).read_text()
        except FileNotFoundError:
            logger.error(f"Prompt file not found at: {prompt_path}")
            raise

        # Ensure logs directory exists
        LOGS_DIR.mkdir(exist_ok=True)

    # impure
    def _audit_log(self, log_data: dict[str, Any]) -> None:
        """Appends a structured log entry to the audit file."""
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(log_data) + "\n")

    # impure: Performs network I/O to an LLM API
    def get_strategy_suggestion(self, history: list[IterationReport]) -> str:
        """
        Gets a strategy suggestion from the configured LLM.

        Args:
            history: A list of previous reports to provide as context.

        Returns:
            The raw JSON string response from the LLM.
        """
        history_str = _format_history(history)
        prompt = self.base_prompt.format(history=history_str)
        temperature = 0.7

        logger.info(f"Calling LLM. Provider: {self.provider}, Model: {self.model}")

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        response = completion.choices[0].message.content
        if not response:
            raise ValueError("LLM returned an empty response.")

        token_count = completion.usage.total_tokens if completion.usage else 0
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        # [H-22] Log the audit trail
        self._audit_log(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "provider": self.provider,
                "model": self.model,
                "prompt_version": self.prompt_version,
                "prompt_hash": prompt_hash,
                "prompt": prompt,  # For full reproducibility
                "temperature": temperature,
                "token_count": token_count,
                "response": response,
            }
        )
        logger.info(f"LLM call successful. Tokens used: {token_count}")

        return response
