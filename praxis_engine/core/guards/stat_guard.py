"""
A guard to check for statistical validity of the signal.
"""
import pandas as pd

from praxis_engine.core.models import Signal, FiltersConfig, ValidationResult, StrategyParamsConfig
from praxis_engine.core.statistics import adf_test, hurst_exponent
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class StatGuard:
    """
    Validates the statistical properties of the price series.
    """

    def __init__(self, filters: FiltersConfig, params: StrategyParamsConfig):
        self.filters = filters
        self.params = params

    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationResult:
        """
        Checks for mean-reverting characteristics using ADF and Hurst tests.
        """
        price_series = df["Close"]
        adf_p_value = adf_test(price_series.pct_change().dropna())
        hurst = hurst_exponent(price_series)

        if adf_p_value is None or adf_p_value > self.filters.adf_p_value_threshold:
            log.warning(f"Stat check failed for signal on {df.index[-1].date()}. ADF p-value: {adf_p_value}")
            return ValidationResult(is_valid=False, stat_check=False, reason="ADF test failed")

        if hurst is None or hurst > self.filters.hurst_threshold:
            log.warning(f"Stat check failed for signal on {df.index[-1].date()}. Hurst: {hurst:.2f}")
            return ValidationResult(is_valid=False, stat_check=False, reason="Hurst exponent too high")

        return ValidationResult(is_valid=True, stat_check=True)
