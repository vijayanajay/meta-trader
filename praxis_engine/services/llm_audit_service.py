"""
Service for interacting with the LLM to get a confidence score.
"""
import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from openai import OpenAI


class LLMAuditService:
    """
    A service to get a confidence score from an LLM based on statistical data.
    """

    def __init__(self, prompt_template_path: str) -> None:
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2:free")
        template_dir = os.path.dirname(prompt_template_path)
        template_file = os.path.basename(prompt_template_path)
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template(template_file)

    def get_confidence_score(self, stats: Dict[str, Any]) -> float:
        """
        Gets a confidence score for a given set of statistics.

        Args:
            stats: A dictionary of statistics to be passed to the prompt.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        prompt = self.template.render(stats)
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
            print(f"Error getting confidence score: {e}")
            return 0.0
