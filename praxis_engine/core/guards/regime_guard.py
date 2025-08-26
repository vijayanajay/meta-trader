"""
A guard to check for a favorable market regime.
"""
import pandas as pd

from praxis_engine.core.models import Signal, FiltersConfig, ValidationResult
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class RegimeGuard:
    """
    Validates the market regime based on sector volatility.
    """

    def __init__(self, filters: FiltersConfig):
        self.filters = filters

    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationResult:
        """
        Checks if the sector volatility is below the configured threshold.
        """
        if signal.sector_vol > self.filters.sector_vol_threshold:
            log.warning(f"Regime check failed for signal on {df.index[-1].date()}. Sector Vol: {signal.sector_vol:.2f}%")
            return ValidationResult(is_valid=False, regime_check=False, reason="High Sector Volatility")

        return ValidationResult(is_valid=True, regime_check=True)
