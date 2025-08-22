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

    def process(
        self,
        data: pd.DataFrame,
        strategy_def: StrategyDefinition,
        trade_size: float,
    ) -> Type[Strategy]:
        """
        Processes the strategy definition against the data to create a new Strategy class.
        """
        import inspect

        local_data = data.copy()
        self._asteval = self._create_asteval_interpreter()
        available_names = set(self._asteval.symtable.keys())

        # Prepare OHLCV data for indicators
        ohlcv = {
            'open': local_data['Open'],
            'high': local_data['High'],
            'low': local_data['Low'],
            'close': local_data['Close'],
            'volume': local_data['Volume'],
        }

        # Calculate indicators
        for indicator in strategy_def.indicators:
            try:
                indicator_func = getattr(ta, indicator.function)

                # Inspect the function signature to provide only required args
                sig = inspect.signature(indicator_func)
                params_to_pass = {
                    p: ohlcv[p] for p in sig.parameters if p in ohlcv
                }

                # Add user-defined params
                params_to_pass.update(indicator.params)

                result = indicator_func(**params_to_pass)
                if result is None:
                    raise ValueError("Indicator function returned None.")

                # Handle multi-column results (e.g., bbands, macd, kc)
                if isinstance(result, pd.DataFrame):
                    for col in result.columns:
                        # Create more intuitive names for common indicators
                        if 'bb' in indicator.function:
                            if 'BBL' in col: name = f"{indicator.name}_lower"
                            elif 'BBM' in col: name = f"{indicator.name}_middle"
                            elif 'BBU' in col: name = f"{indicator.name}_upper"
                            else: name = f"{indicator.name}_{col.replace('.', '_').replace('-', '_')}"
                        elif 'kc' in indicator.function:
                            if 'KCL' in col: name = f"{indicator.name}_lower"
                            elif 'KCM' in col: name = f"{indicator.name}_middle"
                            elif 'KCU' in col: name = f"{indicator.name}_upper"
                            else: name = f"{indicator.name}_{col.replace('.', '_').replace('-', '_')}"
                        elif 'macd' in indicator.function:
                            if 'MACDs' in col: name = f"{indicator.name}_signal"
                            elif 'MACDh' in col: name = f"{indicator.name}_hist"
                            elif 'MACD' in col: name = f"{indicator.name}" # Main line is the least specific, so it goes last
                            else: name = f"{indicator.name}_{col.replace('.', '_').replace('-', '_')}"
                        elif 'adx' in indicator.function:
                            if 'DMP' in col: name = f"{indicator.name}_dmp"
                            elif 'DMN' in col: name = f"{indicator.name}_dmn"
                            elif 'ADX' in col: name = f"{indicator.name}" # Main line is the least specific, so it goes last
                            else: name = f"{indicator.name}_{col.replace('.', '_').replace('-', '_')}"
                        else:
                            # Default generic naming for other multi-column indicators
                            sanitized_col = col.replace('.', '_').replace('-', '_')
                            name = f"{indicator.name}_{sanitized_col}"

                        self._asteval.symtable[name] = result[col].values
                        available_names.add(name)
                else:
                    self._asteval.symtable[indicator.name] = result.values
                    available_names.add(indicator.name)
            except Exception as e:
                raise ValueError(f"Failed to process indicator '{indicator.name}': {e}") from e

        # Add base OHLCV to symbol table
        for name, series in ohlcv.items():
            self._asteval.symtable[name] = series.values
            available_names.add(name)

        # Validate expressions
        self._validate_expression(strategy_def.buy_condition, available_names)
        self._validate_expression(strategy_def.sell_condition, available_names)

        # Evaluate buy and sell conditions
        try:
            buy_signal = self._asteval.eval(strategy_def.buy_condition)
            sell_signal = self._asteval.eval(strategy_def.sell_condition)
        except Exception as e:
            raise ValueError(f"Failed to evaluate conditions: {e}") from e

        # Coerce signals to boolean arrays, handling None from asteval
        if buy_signal is None:
            buy_signal = np.zeros(len(local_data), dtype=bool)
        else:
            buy_signal = np.nan_to_num(buy_signal, nan=0).astype(bool)

        if sell_signal is None:
            sell_signal = np.zeros(len(local_data), dtype=bool)
        else:
            sell_signal = np.nan_to_num(sell_signal, nan=0).astype(bool)


        # Create a dynamic Strategy class
        class DynamicStrategy(Strategy):  # type: ignore[misc]
            trade_size_param = trade_size

            def init(self) -> None:
                self.buy_signal = self.I(lambda: buy_signal)
                self.sell_signal = self.I(lambda: sell_signal)

            def next(self) -> None:
                # Close existing position if sell signal is triggered
                if self.sell_signal and self.position:
                    self.position.close()
                # Enter new long position if buy signal is triggered and we have no open position
                elif self.buy_signal and not self.position:
                    self.buy(size=self.trade_size_param)

        return DynamicStrategy
