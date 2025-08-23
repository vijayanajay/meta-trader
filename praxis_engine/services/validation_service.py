"""
Service for validating a trade signal against a set of guardrails.
"""
from typing import Optional
import pandas as pd

from praxis_engine.core.models import Signal, FiltersConfig, ValidationResult, StrategyParamsConfig
from praxis_engine.core.statistics import adf_test, hurst_exponent
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

class ValidationService:
    """
    Validates a signal against liquidity, market regime, and statistical guardrails.
    """

    def __init__(self, filters: FiltersConfig, params: StrategyParamsConfig):
        self.filters = filters
        self.params = params

    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationResult:
        """
        Runs all validation checks on a given signal.
        """
        # Liquidity Check
        latest_close = df.iloc[-1]["Close"]
        avg_volume = df.iloc[-5:]["Volume"].mean()
        avg_turnover_crores = (avg_volume * latest_close) / 1_00_00_000

        if avg_turnover_crores < self.filters.liquidity_turnover_crores:
            return ValidationResult(is_valid=False, liquidity_check=False, reason="Low Liquidity")

        # Market Regime Check
        if signal.sector_vol > self.filters.sector_vol_threshold:
            return ValidationResult(is_valid=False, regime_check=False, reason="High Sector Volatility")

        # Statistical Validity Check
        adf_p_value = adf_test(df["Close"].pct_change().dropna())
        hurst = hurst_exponent(df["Close"])

        if adf_p_value is None or adf_p_value > self.filters.adf_p_value_threshold:
            return ValidationResult(is_valid=False, stat_check=False, reason="ADF test failed")

        if hurst is None or hurst > self.filters.hurst_threshold:
            return ValidationResult(is_valid=False, stat_check=False, reason="Hurst exponent too high")

        log.info("Signal passed all validation guardrails.")
        return ValidationResult(is_valid=True)
