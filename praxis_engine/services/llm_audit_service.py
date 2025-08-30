import os
import re
from typing import Optional, Dict, Any
import jinja2
import pandas as pd
from openai import OpenAI, APIConnectionError, RateLimitError, AuthenticationError

from praxis_engine.core.models import Signal, ValidationScores, LLMConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.statistics import hurst_exponent

log = get_logger(__name__)

class LLMAuditService:
    """
    A service to connect to an LLM and get a confidence score.
    Adheres to H-2 (Stateless), H-13 (LLM is Blind to Price), H-14 (LLM Audits).
    """

    def __init__(
        self,
        config: LLMConfig,
    ) -> None:
        """
        Initializes the LLMAuditService.
        """
        self.config = config
        self.client = None

        self.llm_provider = os.getenv("LLM_PROVIDER", self.config.provider).strip()
        api_key: Optional[str] = None
        base_url: Optional[str] = None

        if self.llm_provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")
            self.model = os.getenv("OPENROUTER_MODEL", self.config.model)
            log.debug(f"OpenRouter base URL: {base_url}")
        elif self.llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            self.model = self.config.model
        else:
            log.warning(f"LLM_PROVIDER '{self.llm_provider}' is not supported. LLM Audit will be skipped.")
            return

        if not api_key:
            log.warning(f"API key for {self.llm_provider} not found in environment variables. LLM Audit will be skipped.")
            return

        if self.llm_provider == "openrouter":
            log.debug(f"OpenRouter API key loaded: {api_key[:10]}...{api_key[-4:]}")

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)
        log.info(f"Initialized LLM client for {self.llm_provider} with base_url: {base_url}")
        self.prompt_template_path = config.prompt_template_path

    def _parse_llm_response(self, response: Optional[str]) -> float:
        """
        Safely parses the LLM response to extract a float.
        Adheres to H-25 (Constrained LLM Action Space).
        """
        if not response:
            log.warning("LLM response was empty.")
            return 0.0

        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", response)

        if numbers:
            try:
                score = float(numbers[0])
                return max(0.0, min(1.0, score))
            except (ValueError, IndexError):
                log.warning(f"Could not parse float from LLM response: '{response}'")
                return 0.0

        log.warning(f"No numbers found in LLM response: '{response}'")
        return 0.0

    # impure
    def get_confidence_score(
        self,
        historical_stats: Dict[str, Any],
        signal: Signal,
        df_window: pd.DataFrame,
    ) -> float:
        """
        Queries the LLM with a statistical summary to get a confidence score.
        Adheres to H-7 (Side Effects Must Be Labeled).
        """
        if not self.client:
            log.warning("LLM client not initialized, returning score 0.0.")
            return 0.0
        try:
            H = hurst_exponent(df_window["Close"])
            if H is None:
                log.warning("Could not calculate Hurst exponent. Returning score 0.")
                return 0.0

            context = {
                "win_rate": f"{historical_stats.get('win_rate', 0.0):.1f}",
                "profit_factor": f"{historical_stats.get('profit_factor', 0.0):.2f}",
                "sample_size": historical_stats.get("sample_size", 0),
                "sector_volatility": f"{signal.sector_vol:.1f}",
                "hurst_exponent": f"{H:.2f}",
            }

            template_dir = os.path.dirname(self.prompt_template_path)
            template_name = os.path.basename(self.prompt_template_path)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
            template = env.get_template(template_name)
            prompt = template.render(context)
            log.debug(f"LLM Audit Prompt:\n{prompt}")

            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.2,
            )

            if chat_completion and chat_completion.choices:
                response = chat_completion.choices[0].message.content
                log.debug(f"LLM Audit Raw Response: {response}")
            else:
                log.warning("LLM response is empty or invalid.")
                response = None

            score = self._parse_llm_response(response)
            log.info(f"LLM Audit Parsed Score: {score}")
            return score

        except (APIConnectionError, RateLimitError) as e:
            log.error(f"LLM API Error: {e.__class__.__name__}. Returning score 0.")
            return 0.0
        except AuthenticationError as e:
            if self.llm_provider == "openrouter":
                log.error(f"OpenRouter API key error. Please check your OPENROUTER_API_KEY at https://openrouter.ai/keys. Returning score 0.")
            else:
                log.error(f"LLM API Authentication Error: {e}. Returning score 0.")
            return 0.0
        except jinja2.TemplateNotFound:
            log.error(f"Prompt template not found at {self.prompt_template_path}. Returning score 0.")
            return 0.0
        except Exception as e:
            log.critical(f"An unexpected error in get_confidence_score: {e}", exc_info=True)
            return 0.0
