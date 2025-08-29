"""
A guard to check for sufficient liquidity.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig, StrategyParamsConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score

log = get_logger(__name__)


class LiquidityGuard:
    """
    Calculates a liquidity score based on average daily turnover.
    """

    def __init__(self, scoring: ScoringConfig, params: StrategyParamsConfig):
        self.scoring = scoring
        self.params = params

    # impure
    def validate(self, df: pd.DataFrame, signal: Signal) -> float:
        """
        Calculates a score based on the stock's average daily turnover.
        """
        lookback_days = self.params.liquidity_lookback_days
        latest_close = df.iloc[-1]["Close"]
        avg_volume = df.iloc[-lookback_days:]["Volume"].mean()
        avg_turnover_crores = (avg_volume * latest_close) / 1_00_00_000

        score = linear_score(
            value=avg_turnover_crores,
            min_val=self.scoring.liquidity_score_min_turnover_crores,
            max_val=self.scoring.liquidity_score_max_turnover_crores,
        )

        log.debug(
            f"Liquidity score for signal on {df.index[-1].date()}: {score:.2f} "
            f"(Turnover: {avg_turnover_crores:.2f} Cr)"
        )

        return score
