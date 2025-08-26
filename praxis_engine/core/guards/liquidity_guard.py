"""
A guard to check for sufficient liquidity.
"""
import pandas as pd

from praxis_engine.core.models import Signal, FiltersConfig, ValidationResult, StrategyParamsConfig
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class LiquidityGuard:
    """
    Validates a signal for minimum liquidity.
    """

    def __init__(self, filters: FiltersConfig, params: StrategyParamsConfig):
        self.filters = filters
        self.params = params

    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationResult:
        """
        Checks if the stock has sufficient average daily turnover.
        """
        lookback_days = self.params.liquidity_lookback_days
        latest_close = df.iloc[-1]["Close"]
        avg_volume = df.iloc[-lookback_days:]["Volume"].mean()
        avg_turnover_crores = (avg_volume * latest_close) / 1_00_00_000

        if avg_turnover_crores < self.filters.liquidity_turnover_crores:
            log.warning(f"Liquidity check failed for signal on {df.index[-1].date()}. Turnover: {avg_turnover_crores:.2f} Cr")
            return ValidationResult(is_valid=False, liquidity_check=False, reason="Low Liquidity")

        return ValidationResult(is_valid=True, liquidity_check=True)
