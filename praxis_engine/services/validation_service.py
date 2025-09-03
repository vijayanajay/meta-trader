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
    Guards should support the new three-argument signature (full_df, current_index, signal).
    For backward compatibility, implementations may accept `current_index` as optional.
    """
    def validate(self, full_df: pd.DataFrame, current_index: int | None, signal: Signal) -> float:
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


    def validate(self, full_df: pd.DataFrame, *args) -> ValidationScores:
        """
        Runs all guards and collects their scores.

        This method is backward-compatible:
        - new callers should call: validate(full_df, current_index, signal)
        - legacy callers that pass (full_df, signal) are supported as validate(full_df, signal)

        We detect the signature by inspecting args. If two args are provided,
        we assume (current_index, signal). If one arg is provided, we assume
        it's the `signal` and `current_index` will be derived as the last index.
        """
        # Detect calling convention and normalize args for internal use, but
        # preserve the original calling style when invoking individual guards.
        if len(args) == 2:
            # Caller provided (current_index, signal)
            current_index, signal = args
            if not isinstance(current_index, int):
                raise TypeError("current_index must be an int")

            log.info(f"Running validation guards for signal on {full_df.index[current_index].date()}...")

            # Call guards with new three-arg signature
            liquidity_score = self.liquidity_guard.validate(full_df, current_index, signal)
            regime_score = self.regime_guard.validate(full_df, current_index, signal)
            stat_score = self.stat_guard.validate(full_df, current_index, signal)
        elif len(args) == 1:
            # Legacy caller: validate(full_df, signal)
            signal = args[0]
            current_index = len(full_df) - 1

            log.info(f"Running validation guards for signal on {full_df.index[current_index].date()} (legacy call)...")

            # Preserve legacy invocation so tests that mock guard.validate(df, signal)
            # continue to work. The guards themselves are decorated to accept both.
            liquidity_score = self.liquidity_guard.validate(full_df, signal)
            regime_score = self.regime_guard.validate(full_df, signal)
            stat_score = self.stat_guard.validate(full_df, signal)
        else:
            raise TypeError("validate() expects either (full_df, signal) or (full_df, current_index, signal)")

        scores = ValidationScores(
            liquidity_score=liquidity_score,
            regime_score=regime_score,
            stat_score=stat_score,
        )

        log.info(f"Signal scored: {scores}")
        return scores
