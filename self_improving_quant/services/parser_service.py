from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
from asteval import Interpreter
from pydantic import ValidationError

from self_improving_quant.core.models import StrategyDefinition

__all__ = ["SecureStrategyParser"]

logger = logging.getLogger(__name__)


class SecureStrategyParser:
    """
    Parses and validates LLM-generated strategy definitions and securely
    evaluates their trading signals.
    """

    def __init__(self) -> None:
        self.aeval = Interpreter(use_numpy=False)  # Forbid numpy in eval
        # Add more functions to the symbol table if needed, e.g. 'min', 'max'
        # self.aeval.symtable["min"] = min

    def parse_llm_response(self, response_str: str) -> StrategyDefinition | None:
        """
        Safely parses the JSON response from the LLM into a StrategyDefinition.
        """
        try:
            return StrategyDefinition.model_validate(json.loads(response_str))
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse or validate LLM response: {e}")
            return None

    # impure: Modifies the input DataFrame
    def evaluate_signals(self, data: pd.DataFrame, definition: StrategyDefinition) -> pd.DataFrame:
        """
        Evaluates the buy and sell signals on the given data and adds them as
        new boolean columns to the DataFrame.

        This method creates a secure environment for evaluation.
        """
        # 1. Create a symbol table with only the necessary data series
        symtable: dict[str, Any] = {col: data[col] for col in data.columns}

        # 2. Evaluate the buy and sell signals
        try:
            buy_signal_series = self.aeval.eval(definition.buy_signal, symtable=symtable)
            sell_signal_series = self.aeval.eval(definition.sell_signal, symtable=symtable)
        except Exception as e:
            logger.error(f"Error evaluating signal expression: {e}")
            # Return unmodified data on failure
            data["buy_signal"] = False
            data["sell_signal"] = False
            return data

        # 3. Add the boolean series to the DataFrame
        data["buy_signal"] = buy_signal_series
        data["sell_signal"] = sell_signal_series

        return data
