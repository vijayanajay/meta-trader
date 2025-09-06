"""
Service for validating a trade signal by scoring it against a set of guardrails.
"""
import pandas as pd
from typing import Protocol, List

from praxis_engine.core.models import Signal, ScoringConfig, ValidationScores, StrategyParamsConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.liquidity_guard import LiquidityGuard
from praxis_engine.core.guards.regime_guard import RegimeGuard
from praxis_engine.core.guards.stat_guard import StatGuard

log = get_logger(__name__)


class GuardProtocol(Protocol):
    """
    Defines the interface for a validation guard.
    """
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        ...


from praxis_engine.services.regime_model_service import RegimeModelService


class ValidationService:
    """
    Orchestrates a series of guards to score a signal.
    """

    def __init__(
        self,
        scoring_config: ScoringConfig,
        strategy_params: StrategyParamsConfig,
        regime_model_service: RegimeModelService,
    ):
        """
        Initializes the validation service with all required guards.
        """
        self.liquidity_guard = LiquidityGuard(scoring_config, strategy_params)
        self.regime_guard = RegimeGuard(scoring_config, regime_model_service)
        self.stat_guard = StatGuard(scoring_config, strategy_params)


    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> ValidationScores:
        """
        Runs all guards and collects their scores, assuming a dataframe with
        pre-computed indicators is provided.
        """
        log.debug(f"Running validation guards for signal on {full_df.index[current_index].date()}...")

        liquidity_score = self.liquidity_guard.validate(full_df, current_index, signal)
        regime_score = self.regime_guard.validate(full_df, current_index, signal)
        stat_score = self.stat_guard.validate(full_df, current_index, signal)

        scores = ValidationScores(
            liquidity_score=liquidity_score,
            regime_score=regime_score,
            stat_score=stat_score,
        )

        log.debug(f"Signal scored: {scores}")
        return scores
