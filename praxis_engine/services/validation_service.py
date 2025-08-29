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
    def validate(self, df: pd.DataFrame, signal: Signal) -> float:
        ...


class ValidationService:
    """
    Orchestrates a series of guards to score a signal.
    """

    def __init__(self, scoring: ScoringConfig, params: StrategyParamsConfig):
        """
        Initializes the validation service with all required guards.
        """
        self.liquidity_guard = LiquidityGuard(scoring, params)
        self.regime_guard = RegimeGuard(scoring)
        self.stat_guard = StatGuard(scoring, params)


    def validate(self, df: pd.DataFrame, signal: Signal) -> ValidationScores:
        """
        Runs all guards and collects their scores.
        """
        log.info(f"Running validation guards for signal on {df.index[-1].date()}...")

        liquidity_score = self.liquidity_guard.validate(df, signal)
        regime_score = self.regime_guard.validate(df, signal)
        stat_score = self.stat_guard.validate(df, signal)

        scores = ValidationScores(
            liquidity_score=liquidity_score,
            regime_score=regime_score,
            stat_score=stat_score,
        )

        log.info(f"Signal scored: {scores}")
        return scores
