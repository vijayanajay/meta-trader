import os
import json
import logging
import re
from typing import List, cast, Optional

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
    def get_suggestion(
        self,
        ticker: str,
        history: List[PerformanceReport],
        failed_strategy: Optional[PerformanceReport],
        best_strategy_so_far: StrategyDefinition,
    ) -> StrategyDefinition:
        """
        Gets a new strategy suggestion from the LLM.
        """
        prompt = self._build_prompt(ticker, history, failed_strategy, best_strategy_so_far)

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
            if not response_content:
                raise ValueError("LLM returned empty response.")

            if completion.usage:
                logger.info(
                    f"LLM usage: Prompt tokens: {completion.usage.prompt_tokens}, "
                    f"Completion tokens: {completion.usage.completion_tokens}"
                )

            json_response = json.loads(response_content)
            return StrategyDefinition.model_validate(json_response)

        except APIError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse/validate LLM response: {e}\nRaw response: {response_content}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while communicating with the LLM: {e}")
            raise

    def _build_prompt(
        self,
        ticker: str,
        history: List[PerformanceReport],
        failed_strategy: Optional[PerformanceReport],
        best_strategy_so_far: StrategyDefinition,
    ) -> str:
        """Constructs the full prompt string for the LLM."""

        failure_context = ""
        if failed_strategy:
            failed_strat_json = failed_strategy.strategy.model_dump_json(indent=2)
            failure_context = (
                "CRITICAL FEEDBACK: Your previous suggestion was a failure and has been pruned.\n"
                f"Failed Strategy JSON: {failed_strat_json}\n"
                f"This strategy resulted in a Sharpe Ratio of {failed_strategy.performance.sharpe_ratio:.2f}, "
                "which is below the required threshold. This result has been discarded.\n"
                "We are reverting to the previous best strategy as the context. "
                "Analyze the failure and propose a substantially different approach.\n\n"
            )

        formatted_history = self._format_history(history)

        return self.prompt_template.format(
            ticker=ticker,
            failure_context=failure_context,
            history=formatted_history,
            best_strategy_json=best_strategy_so_far.model_dump_json(indent=2),
        )

    def _format_history(self, history: List[PerformanceReport]) -> str:
        """Formats the history of reports into a string for the prompt."""
        if not history:
            return "No history yet. This is the first iteration. Please provide the baseline strategy."

        # Summarize older reports, show more detail for recent ones
        history_parts = []
        for i, report in enumerate(history):
            if report.is_pruned:
                report_str = (
                    f"Iteration {i}: SKIPPED (Strategy failed with Sharpe Ratio "
                    f"{report.performance.sharpe_ratio:.2f} and was pruned)"
                )
            else:
                report_str = (
                    f"Iteration {i}:\n"
                    f"  Strategy Name: {report.strategy.strategy_name}\n"
                    f"  Sharpe Ratio: {report.performance.sharpe_ratio:.2f}\n"
                    f"  Annual Return: {report.performance.annual_return_pct:.2f}%\n"
                    f"  Max Drawdown: {report.performance.max_drawdown_pct:.2f}%\n"
                    f"  Total Trades: {report.trade_summary.total_trades}"
                )
            history_parts.append(report_str)

        return "\n\n".join(history_parts)
