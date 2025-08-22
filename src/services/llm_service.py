"""
This service handles all interactions with the configured LLM.
"""
import os
import json
import logging
from typing import List, cast

from openai import OpenAI, APIError
from dotenv import load_dotenv

from core.models import PerformanceReport, StrategyDefinition

__all__ = ["LLMService"]

# It's better to have a logger configured at the application level,
# but for a service, we can create a default logger.
logger = logging.getLogger(__name__)


class LLMService:
    """
    Manages all communication with the LLM API.
    """

    def __init__(self) -> None:
        load_dotenv()
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        api_key = None
        base_url = None

        if self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            self.model = os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2:free")
            base_url = os.getenv("OPENROUTER_BASE_URL")
        else: # Default to openai
            api_key = os.getenv("OPENAI_API_KEY")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")

        if not api_key:
            raise ValueError(f"API key for {self.provider} not found in .env file.")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        try:
            with open("src/prompts/quant_analyst.txt", "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.error("Prompt template file not found.")
            raise

    def _format_history(self, history: List[PerformanceReport]) -> str:
        """Formats the history of reports into a string for the prompt."""
        if not history:
            return "No history available. This is the first iteration."

        formatted_reports = []
        for i, report in enumerate(history):
            report_str = (
                f"Iteration {i}:\n"
                f"  Strategy: {report.strategy.model_dump_json()}\n"
                f"  Sharpe Ratio: {report.sharpe_ratio:.2f}\n"
                f"  Annual Return: {report.annual_return_pct:.2f}%\n"
                f"  Max Drawdown: {report.max_drawdown_pct:.2f}%\n"
                f"  Total Trades: {report.trade_summary.total_trades}\n"
            )
            formatted_reports.append(report_str)

        return "\n---\n".join(formatted_reports)

    # impure
    def get_suggestion(self, history: List[PerformanceReport]) -> StrategyDefinition:
        """
        Sends the history to the LLM and gets a new strategy suggestion.
        """
        history_str = self._format_history(history)
        prompt = self.prompt_template.format(history=history_str)

        try:
            logger.info(f"Sending request to LLM ({self.model})...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a quantitative analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )

            usage = completion.usage
            if usage:
                logger.info(
                    f"LLM call successful. Tokens: "
                    f"Prompt={usage.prompt_tokens}, "
                    f"Completion={usage.completion_tokens}, "
                    f"Total={usage.total_tokens}"
                )

            response_text = completion.choices[0].message.content
            if not response_text:
                raise ValueError("LLM returned an empty response.")

            # The prompt asks for JSON only, so we parse it directly.
            json_response = json.loads(response_text)

            # Use Pydantic for validation
            strategy_def = StrategyDefinition(**json_response)
            return strategy_def

        except APIError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {response_text}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in LLMService: {e}")
            raise
