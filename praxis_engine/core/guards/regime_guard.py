"""
A guard to calculate a score based on market regime.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score

log = get_logger(__name__)


class RegimeGuard:
    """
    Calculates a regime score based on sector volatility.
    """

    def __init__(self, scoring: ScoringConfig):
        self.scoring = scoring

    # impure
    def validate(self, df: pd.DataFrame, signal: Signal) -> float:
        """
        Calculates a score based on the sector volatility. Lower is better.
        """
        score = linear_score(
            value=signal.sector_vol,
            min_val=self.scoring.regime_score_min_volatility_pct,
            max_val=self.scoring.regime_score_max_volatility_pct,
        )

        log.debug(
            f"Regime score for signal on {df.index[-1].date()}: {score:.2f} "
            f"(Sector Vol: {signal.sector_vol:.2f}%)"
        )

        return score
