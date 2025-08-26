"""
Service for validating a trade signal against a set of guardrails.
"""
import pandas as pd

from praxis_engine.core.models import Signal, FiltersConfig, ValidationResult, StrategyParamsConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.liquidity_guard import LiquidityGuard
from praxis_engine.core.guards.regime_guard import RegimeGuard
from praxis_engine.core.guards.stat_guard import StatGuard

log = get_logger(__name__)


class ValidationService:
    """
    Orchestrates a series of guards to validate a signal.
    """

    def __init__(self, filters: FiltersConfig, params: StrategyParamsConfig):
        """
        Initializes the validation service with all required guards.
        """
        self.guards = [
            LiquidityGuard(filters, params),
            RegimeGuard(filters),
            StatGuard(filters, params),
        ]

    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationResult:
        """
        Runs all validation checks sequentially on a given signal.
        If any guard fails, the process stops and returns the failure reason.
        """
        log.info(f"Running validation guards for signal on {df.index[-1].date()}...")
        for guard in self.guards:
            result = guard.validate(df, signal)
            if not result.is_valid:
                return result

        log.info("Signal passed all validation guardrails.")
        return ValidationResult(is_valid=True)
