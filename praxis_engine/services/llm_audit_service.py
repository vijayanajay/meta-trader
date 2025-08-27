"""
Service for interacting with the LLM to audit statistical summaries.
"""
import os
import re
from typing import Optional, Dict, Any
import jinja2
import pandas as pd
from openai import OpenAI, APIConnectionError, RateLimitError

from praxis_engine.core.models import Signal, ValidationResult, LLMConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.statistics import hurst_exponent
from praxis_engine.services.signal_engine import SignalEngine
from praxis_engine.services.validation_service import ValidationService
from praxis_engine.services.execution_simulator import ExecutionSimulator

log = get_logger(__name__)

class LLMAuditService:
    """
    A service to connect to an LLM and get a confidence score.
    Adheres to H-2 (Stateless), H-13 (LLM is Blind to Price), H-14 (LLM Audits).
    """

    def __init__(
        self,
        config: LLMConfig,
        signal_engine: SignalEngine,
        validation_service: ValidationService,
        execution_simulator: ExecutionSimulator,
    ) -> None:
        """
        Initializes the LLMAuditService.
        """
        self.config = config
        self.signal_engine = signal_engine
        self.validation_service = validation_service
        self.execution_simulator = execution_simulator

        llm_provider = os.getenv("LLM_PROVIDER", "openai")
        api_key: Optional[str] = None
        base_url: Optional[str] = None

        if llm_provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL")
            self.model = os.getenv("OPENROUTER_MODEL", self.config.model)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            self.model = self.config.model

        if not api_key:
            raise ValueError(f"API key for {llm_provider} not found in environment variables.")

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)
        self.prompt_template_path = config.prompt_template_path

    def _calculate_historical_performance(
        self, df_window: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Runs a mini-backtest on the historical window to get performance stats.
        This method contains the simulation logic to avoid data leakage.
        """
        returns = []
        min_history_days = self.signal_engine.params.min_history_days
        exit_days = self.signal_engine.params.exit_days

        for i in range(min_history_days, len(df_window) - exit_days):
            historical_sub_window = df_window.iloc[0:i]
            if len(historical_sub_window) < min_history_days:
                continue

            signal = self.signal_engine.generate_signal(historical_sub_window.copy())
            if not signal:
                continue

            validation = self.validation_service.validate(historical_sub_window, signal)
            if not validation.is_valid:
                continue

            # --- Perform cost-aware simulation for this historical trade ---
            entry_price = df_window.iloc[i]["Open"]
            exit_price = df_window.iloc[i + exit_days]["Close"]
            volume = df_window.iloc[i]["Volume"]

            net_return = self.execution_simulator.calculate_net_return(
                entry_price=entry_price, exit_price=exit_price, daily_volume=volume
            )
            returns.append(net_return)

        if not returns:
            return {"win_rate": 0.0, "profit_factor": 0.0, "sample_size": 0}

        wins = [r for r in returns if r > 0.0177]
        losses = [r for r in returns if r <= 0]

        win_rate = len(wins) / len(returns) if returns else 0.0

        total_profit = sum(wins)
        total_loss = abs(sum(losses))

        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        return {
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "sample_size": len(returns),
        }

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
        self, df_window: pd.DataFrame, signal: Signal, validation: ValidationResult
    ) -> float:
        """
        Queries the LLM with a statistical summary to get a confidence score.
        Adheres to H-7 (Side Effects Must Be Labeled).
        """
        try:
            H = hurst_exponent(df_window["Close"])
            if H is None:
                log.warning("Could not calculate Hurst exponent. Returning score 0.")
                return 0.0

            historical_stats = self._calculate_historical_performance(df_window)

            context = {
                "win_rate": f"{historical_stats['win_rate']:.1f}",
                "profit_factor": f"{historical_stats['profit_factor']:.2f}"
                if historical_stats["profit_factor"] != float("inf")
                else "Infinity",
                "sample_size": historical_stats["sample_size"],
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

            response = chat_completion.choices[0].message.content
            log.debug(f"LLM Audit Raw Response: {response}")

            score = self._parse_llm_response(response)
            log.info(f"LLM Audit Parsed Score: {score}")
            return score

        except (APIConnectionError, RateLimitError) as e:
            log.error(f"LLM API Error: {e.__class__.__name__}. Returning score 0.")
            return 0.0
        except jinja2.TemplateNotFound:
            log.error(f"Prompt template not found at {self.prompt_template_path}. Returning score 0.")
            return 0.0
        except Exception as e:
            log.critical(f"An unexpected error in get_confidence_score: {e}", exc_info=True)
            return 0.0
