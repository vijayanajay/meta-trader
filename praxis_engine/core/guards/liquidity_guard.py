"""
A guard to check for sufficient liquidity.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig, StrategyParamsConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score
from praxis_engine.core.guards.decorators import normalize_guard_args

log = get_logger(__name__)


class LiquidityGuard:
    """
    Calculates a liquidity score based on average daily turnover.
    """

    def __init__(self, scoring: ScoringConfig, params: StrategyParamsConfig):
        self.scoring = scoring
        self.params = params

    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """Calculates a score based on the stock's average daily turnover using an index-based lookup."""
        lookback_days = self.params.liquidity_lookback_days
        if current_index - lookback_days + 1 < 0:
            # Not enough history
            return 0.0

        latest_close = full_df.iloc[current_index]["Close"]
        avg_volume = full_df.iloc[current_index - lookback_days + 1: current_index + 1]["Volume"].mean()
        avg_turnover_crores = (avg_volume * latest_close) / 1_00_00_000

        score = linear_score(
            value=avg_turnover_crores,
            min_val=self.scoring.liquidity_score_min_turnover_crores,
            max_val=self.scoring.liquidity_score_max_turnover_crores,
        )

        log.debug(
            f"Liquidity score for signal on {full_df.index[current_index].date()}: {score:.2f} "
            f"(Turnover: {avg_turnover_crores:.2f} Cr)"
        )

        return score
