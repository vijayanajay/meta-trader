"""
Service for interacting with the LLM to audit statistical summaries.
"""
import os
from typing import Optional
import jinja2
import pandas as pd
from openai import OpenAI

from typing import Dict, Any

import pandas as pd
import jinja2
from openai import OpenAI

from praxis_engine.core.models import Signal, ValidationResult, LLMConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.statistics import hurst_exponent
from praxis_engine.services.signal_engine import SignalEngine
from praxis_engine.services.validation_service import ValidationService
from praxis_engine.services.execution_simulator import ExecutionSimulator

log = get_logger(__name__)

class LLMAuditService:
    """
    A service to connect to a local LLM and get a confidence score.
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

        # Initialize the LLM client
        llm_provider = os.getenv("LLM_PROVIDER", "openai")
        api_key = (
            os.getenv("OPENROUTER_API_KEY")
            if llm_provider == "openrouter"
            else os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            os.getenv("OPENROUTER_BASE_URL")
            if llm_provider == "openrouter"
            else None
        )

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = config.model
        self.prompt_template_path = config.prompt_template_path

    def _calculate_historical_performance(
        self, df_window: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Runs a mini-backtest on the historical window to get performance stats.
        """
        trades = []
        min_history_days = self.signal_engine.params.min_history_days
        exit_days = self.signal_engine.params.exit_days

        # Loop through the historical window to find past signals and their outcomes
        for i in range(min_history_days, len(df_window) - exit_days):
            historical_sub_window = df_window.iloc[0:i]
            signal = self.signal_engine.generate_signal(historical_sub_window.copy())
            if not signal:
                continue

            validation = self.validation_service.validate(historical_sub_window, signal)
            if not validation.is_valid:
                continue

            # Simulate the trade to get the outcome
            entry_price = df_window.iloc[i]["Open"]
            exit_price = df_window.iloc[i + exit_days]["Close"]

            # Simplified simulation for performance calculation
            net_return_pct = (exit_price - entry_price) / entry_price
            trades.append(net_return_pct)

        if not trades:
            return {"win_rate": 0, "profit_factor": 0, "sample_size": 0}

        wins = [t for t in trades if t > 0.0177]  # Win is > 1.77% net return
        losses = [t for t in trades if t <= 0]

        win_rate = len(wins) / len(trades)

        total_profit = sum(wins)
        total_loss = abs(sum(losses))

        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "sample_size": len(trades),
        }

    def get_confidence_score(
        self, df_window: pd.DataFrame, signal: Signal, validation: ValidationResult
    ) -> float:
        """
        Queries the LLM with a statistical summary to get a confidence score.
        """
        try:
            # 1. Calculate Hurst Exponent
            H = hurst_exponent(df_window["Close"])
            if H is None:
                log.warning("Could not calculate Hurst exponent. Returning score 0.")
                return 0.0

            # 2. Calculate historical performance
            # This is where the complex part will be implemented.
            # For now, we use a placeholder.
            historical_stats = self._calculate_historical_performance(df_window)

            # Prepare the context for the prompt template
            context = {
                "win_rate": historical_stats["win_rate"],
                "profit_factor": historical_stats["profit_factor"],
                "sample_size": historical_stats["sample_size"],
                "sector_vol": signal.sector_vol,
                "hurst_exponent": H,
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
