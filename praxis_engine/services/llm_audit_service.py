"""
Service for interacting with the LLM to audit statistical summaries.
"""
import os
from typing import Optional
import jinja2
import pandas as pd
from openai import OpenAI

from praxis_engine.core.models import Signal, ValidationResult, LLMConfig
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

class LLMAuditService:
    """
    A service to connect to a local LLM and get a confidence score.
    """

    def __init__(self, config: LLMConfig) -> None:
        """
        Initializes the LLMAuditService.
        """
        self.client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = config.model
        self.prompt_template_path = config.prompt_template_path
        self.confidence_threshold = config.confidence_threshold


    def get_confidence_score(
        self, df_window: pd.DataFrame, signal: Signal, validation: ValidationResult
    ) -> float:
        """
        Queries the LLM with a statistical summary to get a confidence score.
        """
        try:
            # Prepare the context for the prompt template
            context = {
                "win_rate": 0.5, # Placeholder
                "profit_factor": 1.5, # Placeholder
                "sample_size": 20, # Placeholder
                "sector_vol": signal.sector_vol,
                "hurst_exponent": 0.4, # Placeholder
            }

            # Load and render the prompt template
            template_dir = os.path.dirname(self.prompt_template_path)
            template_name = os.path.basename(self.prompt_template_path)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
            template = env.get_template(template_name)
            prompt = template.render(context)

            # Query the LLM
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )

            response = chat_completion.choices[0].message.content
            # The LLM is instructed to return a single float.
            return float(response)
        except Exception as e:
            log.error(f"Error getting confidence score: {e}")
            return 0.0
