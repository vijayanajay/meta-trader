from __future__ import annotations

import logging
from typing import Type

import pandas_ta as ta
from backtesting import Strategy

from self_improving_quant.core.models import StrategyDefinition

__all__ = ["create_strategy_class"]

logger = logging.getLogger(__name__)


def create_strategy_class(definition: StrategyDefinition) -> Type[Strategy]:
    """
    Dynamically creates a backtesting.py Strategy class from a definition.

    This version expects the buy/sell signals to be pre-calculated boolean
    columns in the input data, prepared by the SecureStrategyParser.
    """

    class CustomStrategy(Strategy):  # type: ignore[misc]
        """A dynamically created strategy based on LLM suggestions."""

        # impure: Modifies the class state during init
        def init(self) -> None:
            """Initialize indicators."""
            for indicator in definition.indicators:
                try:
                    # e.g., self.data.df['SMA_10'] = ta.sma(self.data.Close, length=10)
                    indicator_func = getattr(ta, indicator["type"])
                    params = indicator.get("params", {})
                    result = indicator_func(self.data.Close, **params)

                    # For indicators that return a DataFrame, take the first column
                    if isinstance(result, ta.pd.DataFrame):
                        # Ensure column name for multi-output indicators is descriptive
                        main_col_name = result.columns[0]
                        self.data.df[indicator["name"]] = result[main_col_name]
                    else:
                        self.data.df[indicator["name"]] = result
                except Exception as e:
                    logger.error(f"Error initializing indicator {indicator['name']}: {e}")

        # impure: Modifies internal trade state
        def next(self) -> None:
            """Define the trading logic based on pre-calculated signals."""
            # The SecureStrategyParser must have already added these columns
            if self.data.df["buy_signal"].iloc[-1]:
                self.buy()
            elif self.data.df["sell_signal"].iloc[-1]:
                self.sell()

    return CustomStrategy
