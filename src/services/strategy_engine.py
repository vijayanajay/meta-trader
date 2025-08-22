from typing import Type, Any, Dict
import numpy as np
import pandas as pd
import pandas_ta as ta
from asteval import Interpreter, get_ast_names
from backtesting import Strategy
from backtesting.lib import crossover

from core.models import StrategyDefinition


class StrategyEngine:
    """
    Processes a strategy definition to create a dynamic backtesting.py Strategy class.

    This engine is designed to be secure, using `asteval` to safely evaluate
    buy/sell conditions provided in the strategy definition, preventing arbitrary
    code execution.
    """

    def __init__(self) -> None:
        """Initializes the StrategyEngine."""
        self._asteval = self._create_asteval_interpreter()

    def _create_asteval_interpreter(self) -> Interpreter:
        """Creates a sandboxed asteval interpreter."""
        # For security, start with a completely empty symbol table
        asteval_interpreter = Interpreter(symtable={})
        # Explicitly grant access to safe functions/objects
        asteval_interpreter.symtable['crossover'] = crossover
        asteval_interpreter.symtable['True'] = True
        asteval_interpreter.symtable['False'] = False
        asteval_interpreter.symtable['None'] = None
        return asteval_interpreter

    def _validate_expression(self, expression: str, available_names: set[str]) -> None:
        """
        Validates that the expression only uses names available in the symbol table.
        """
        try:
            names = get_ast_names(self._asteval.parse(expression))
            for name in names:
                if name not in available_names:
                    raise NameError(f"Name '{name}' is not defined in the strategy context.")
        except Exception as e:
            raise ValueError(f"Invalid expression '{expression}': {e}") from e

    def process(self, data: pd.DataFrame, strategy_def: StrategyDefinition) -> Type[Strategy]:
        """
        Processes the strategy definition against the data to create a new Strategy class.

        Args:
            data: The OHLCV data for the asset.
            strategy_def: The strategy definition object.

        Returns:
            A new class that inherits from backtesting.py's Strategy, with the
            logic from the strategy definition applied.
        """
        local_data = data.copy()

        # Reset the symbol table for each run to avoid state leakage
        self._asteval = self._create_asteval_interpreter()

        available_names = set(self._asteval.symtable.keys())

        # Calculate indicators and add them to the symbol table
        indicator_series: Dict[str, pd.Series] = {}
        for indicator in strategy_def.indicators:
            try:
                indicator_func = getattr(ta, indicator.function)
                result = indicator_func(local_data['Close'], **indicator.params)
                if result is None:
                    raise ValueError("Indicator function returned None.")

                # If the indicator returns a DataFrame (like MACD), add each column
                if isinstance(result, pd.DataFrame):
                    for col in result.columns:
                        name = f"{indicator.name}_{col}"
                        indicator_series[name] = result[col]
                        self._asteval.symtable[name] = result[col].values
                        available_names.add(name)
                else:
                    indicator_series[indicator.name] = result
                    self._asteval.symtable[indicator.name] = result.values
                    available_names.add(indicator.name)
            except Exception as e:
                raise ValueError(f"Failed to process indicator '{indicator.name}': {e}") from e

        # Add OHLCV data to the symbol table
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            name = col.lower()
            self._asteval.symtable[name] = local_data[col].values
            available_names.add(name)

        # Validate expressions before evaluation
        self._validate_expression(strategy_def.buy_condition, available_names)
        self._validate_expression(strategy_def.sell_condition, available_names)

        # Evaluate buy and sell conditions
        try:
            buy_signal = self._asteval.eval(strategy_def.buy_condition)
            sell_signal = self._asteval.eval(strategy_def.sell_condition)
        except Exception as e:
            raise ValueError(f"Failed to evaluate conditions: {e}") from e

        # Coerce signals to boolean arrays
        buy_signal = np.nan_to_num(buy_signal, nan=0).astype(bool)
        sell_signal = np.nan_to_num(sell_signal, nan=0).astype(bool)


        # Create a dynamic Strategy class
        class DynamicStrategy(Strategy): # type: ignore[misc]
            def init(self) -> None:
                self.buy_signal = self.I(lambda: buy_signal)
                self.sell_signal = self.I(lambda: sell_signal)

            def next(self) -> None:
                if self.buy_signal:
                    self.buy()
                elif self.sell_signal:
                    self.sell()

        return DynamicStrategy
