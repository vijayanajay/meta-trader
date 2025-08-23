from typing import Type, Any, Dict
import numpy as np
import pandas as pd
from asteval import Interpreter, get_ast_names
from backtesting import Strategy
from backtesting.lib import crossover

from core.models import StrategyDefinition
from core.indicators import sma, ema, rsi, macd, bbands, kc, adx

INDICATOR_MAPPING = {
    "sma": sma,
    "ema": ema,
    "rsi": rsi,
    "macd": macd,
    "bbands": bbands,
    "kc": kc,
    "adx": adx,
}


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
        asteval_interpreter = Interpreter(symtable={})
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
                indicator_func = INDICATOR_MAPPING.get(indicator.function)
                if indicator_func is None:
                    raise ValueError(f"Indicator '{indicator.function}' is not supported.")

                sig = inspect.signature(indicator_func)
                params_to_pass = {
                    p: ohlcv[p] for p in sig.parameters if p in ohlcv
                }
                if 'series' in sig.parameters: # Handle single-series indicators like rsi, sma
                    params_to_pass['series'] = ohlcv['close']

                params_to_pass.update(indicator.params)

                result = indicator_func(**params_to_pass)
                if result is None:
                    raise ValueError("Indicator function returned None.")

                # Handle multi-column results (e.g., bbands, macd, kc)
                if isinstance(result, pd.DataFrame):
                    for col in result.columns:
                        if 'bb' in indicator.function:
                            if 'BBL' in col: name = f"{indicator.name}_lower"
                            elif 'BBM' in col: name = f"{indicator.name}_middle"
                            elif 'BBU' in col: name = f"{indicator.name}_upper"
                            else: name = f"{indicator.name}_{col}"
                        elif 'kc' in indicator.function:
                            if 'KCL' in col: name = f"{indicator.name}_lower"
                            elif 'KCM' in col: name = f"{indicator.name}_middle"
                            elif 'KCU' in col: name = f"{indicator.name}_upper"
                            else: name = f"{indicator.name}_{col}"
                        elif 'macd' in indicator.function:
                            if 'MACDs' in col: name = f"{indicator.name}_signal"
                            elif 'MACDh' in col: name = f"{indicator.name}_hist"
                            elif 'MACD' in col: name = f"{indicator.name}"
                            else: name = f"{indicator.name}_{col}"
                        elif 'adx' in indicator.function:
                            if 'DMP' in col: name = f"{indicator.name}_dmp"
                            elif 'DMN' in col: name = f"{indicator.name}_dmn"
                            elif 'ADX' in col: name = f"{indicator.name}"
                            else: name = f"{indicator.name}_{col}"
                        else:
                            name = f"{indicator.name}_{col}"

                        self._asteval.symtable[name] = result[col].values
                        available_names.add(name)
                else:
                    self._asteval.symtable[indicator.name] = result.values
                    available_names.add(indicator.name)
            except Exception as e:
                raise ValueError(f"Failed to process indicator '{indicator.name}': {e}") from e

        for name, series in ohlcv.items():
            self._asteval.symtable[name.capitalize()] = series.values
            available_names.add(name.capitalize())

        self._validate_expression(strategy_def.buy_condition, available_names)
        self._validate_expression(strategy_def.sell_condition, available_names)

        try:
            buy_signal = self._asteval.eval(strategy_def.buy_condition)
            sell_signal = self._asteval.eval(strategy_def.sell_condition)
        except Exception as e:
            raise ValueError(f"Failed to evaluate conditions: {e}") from e

        if buy_signal is None:
            buy_signal = np.zeros(len(local_data), dtype=bool)
        else:
            buy_signal = np.nan_to_num(buy_signal, nan=0).astype(bool)

        if sell_signal is None:
            sell_signal = np.zeros(len(local_data), dtype=bool)
        else:
            sell_signal = np.nan_to_num(sell_signal, nan=0).astype(bool)


        class DynamicStrategy(Strategy):
            trade_size_param = trade_size

            def init(self) -> None:
                self.buy_signal = self.I(lambda: buy_signal)
                self.sell_signal = self.I(lambda: sell_signal)

            def next(self) -> None:
                if self.sell_signal and self.position:
                    self.position.close()
                elif self.buy_signal and not self.position:
                    self.buy(size=self.trade_size_param)

        return DynamicStrategy
