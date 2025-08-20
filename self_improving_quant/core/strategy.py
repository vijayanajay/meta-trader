from __future__ import annotations

from typing import Type

# HACK: Monkey-patch numpy for a bug in an old version of pandas-ta
# This is to address: ImportError: cannot import name 'NaN' from 'numpy'
# This should be removed once pandas-ta is updated.
import numpy
if not hasattr(numpy, "NaN"):
    setattr(numpy, "NaN", numpy.nan)

import pandas_ta as ta
from asteval import Interpreter
from backtesting import Strategy

from self_improving_quant.core.models import StrategyDefinition

__all__ = ["create_strategy_class"]


def create_strategy_class(definition: StrategyDefinition) -> Type[Strategy]:
    """
    Dynamically creates a backtesting.py Strategy class from a definition.
    """

    class CustomStrategy(Strategy):  # type: ignore[misc]
        """A dynamically created strategy based on LLM suggestions."""

        # impure: Modifies the class state during init
        def init(self) -> None:
            """Initialize indicators."""
            self.aeval = Interpreter(symtable={"self": self})
            for indicator in definition.indicators:
                try:
                    # e.g., self.data.df['SMA_10'] = ta.sma(self.data.Close, length=10)
                    indicator_func = getattr(ta, indicator["type"])
                    params = indicator.get("params", {})
                    # Assume the main input is always the 'Close' price for simplicity
                    result = indicator_func(self.data.Close, **params)
                    # For indicators that return a DataFrame, take the first column
                    if isinstance(result, ta.pd.DataFrame):
                        self.data.df[indicator["name"]] = result.iloc[:, 0]
                    else:
                        self.data.df[indicator["name"]] = result
                except Exception as e:
                    # This helps debug bad indicator suggestions from the LLM
                    print(f"Error initializing indicator {indicator['name']}: {e}")

        # impure: Modifies internal trade state
        def next(self) -> None:
            """Define the trading logic."""
            try:
                # Evaluate buy and sell signals in the asteval sandbox
                if self.aeval.eval(definition.buy_signal):
                    self.buy()
                elif self.aeval.eval(definition.sell_signal):
                    self.sell()
            except Exception as e:
                # This helps debug bad signal suggestions from the LLM
                print(f"Error evaluating signal: {e}")

    return CustomStrategy
