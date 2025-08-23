"""
Service for interacting with the LLM to get a confidence score.
"""
import os
from typing import Any, Dict

from openai import OpenAI

from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class LLMAuditService:
    """
    A service to get a confidence score from an LLM based on statistical data.
    """

    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2:free")
        self.prompt_template = (
            "You are a quantitative analyst AI. Your task is to provide a confidence score on a "
            "potential mean-reversion trade signal based on its historical performance characteristics.\n\n"
            "**Do not provide any explanation or commentary. Your response must be a single "
            "floating-point number between 0.0 and 1.0.**\n\n"
            "Here are the statistics for the signal on a given stock:\n"
            "- Historical Win Rate (>1.77% net return in 20 days): {win_rate}%\n"
            "- Historical Profit Factor: {profit_factor}\n"
            "- Historical Sample Size (number of past signals): {sample_size}\n"
            "- Current Sector Volatility (annualized): {sector_volatility}%\n"
            "- Current Hurst Exponent: {hurst_exponent}\n\n"
            "Based on these statistics, what is the confidence that this signal is not a "
            "statistical anomaly and is likely to be a profitable trade?\n\n"
            "Confidence Score:"
        )

    def get_confidence_score(self, stats: Dict[str, Any]) -> float:
        """
        Gets a confidence score for a given set of statistics.

        Args:
            stats: A dictionary of statistics to be passed to the prompt.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        prompt = self.prompt_template.format(**stats)
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0,
                max_tokens=10,
            )
            response_text = chat_completion.choices[0].message.content
            if response_text:
                return float(response_text.strip())
            return 0.0
        except Exception as e:
            log.error(f"Error getting confidence score: {e}")
            return 0.0
