import os
import json
import logging
import re
from typing import List, cast

from openai import OpenAI, APIError
from dotenv import load_dotenv
from pydantic import ValidationError

from core.models import PerformanceReport, StrategyDefinition

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    """
    A service to interact with an LLM to get trading strategy suggestions.
    """
    __all__ = ['LLMService']

    def __init__(self) -> None:
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

        if not self.model:
            raise ValueError(f"Model for {self.provider} not found in .env file.")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        try:
            with open("src/prompts/quant_analyst.txt", "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.error("Prompt file not found at src/prompts/quant_analyst.txt")
            raise

    # impure
    def get_suggestion(self, history: List[PerformanceReport]) -> StrategyDefinition:
        """
        Gets a new strategy suggestion from the LLM.

        Args:
            history: A list of performance reports from previous iterations.

        Returns:
            A StrategyDefinition object representing the new strategy.
        """
        formatted_history = self._format_history(history)
        prompt = self.prompt_template.format(history=formatted_history)

        try:
            logger.info(f"Sending prompt to LLM ({self.model})...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a world-class quantitative analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            response_content = completion.choices[0].message.content
            if response_content is None:
                raise ValueError("LLM returned empty response.")

            if completion.usage:
                logger.info(f"LLM usage: Prompt tokens: {completion.usage.prompt_tokens}, Completion tokens: {completion.usage.completion_tokens}")

            json_response = json.loads(response_content)
            strategy_def = StrategyDefinition.model_validate(json_response)
            return strategy_def

        except APIError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse or validate LLM response: {e}")
            logger.debug(f"Raw LLM response: {response_content}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while communicating with the LLM: {e}")
            raise

    def _format_history(self, history: List[PerformanceReport]) -> str:
        if not history:
            return "No history yet. This is the first iteration. Please provide the baseline strategy."

        formatted_reports = []
        for i, report in enumerate(history):
            strategy_def_json = report.strategy.model_dump_json(indent=2)

            report_str = f"Iteration {i}:\n"
            report_str += f"  Strategy: {strategy_def_json}\n"
            report_str += f"  Sharpe Ratio: {report.sharpe_ratio:.2f}\n"
            report_str += f"  Win Rate: {report.trade_summary.win_rate_pct:.2f}%\n"
            report_str += f"  Total Trades: {report.trade_summary.total_trades}\n"
            formatted_reports.append(report_str)

        return "\n".join(formatted_reports)
