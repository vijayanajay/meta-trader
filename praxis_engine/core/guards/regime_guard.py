"""
A guard to calculate a score based on market regime.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score
from praxis_engine.core.guards.decorators import normalize_guard_args

log = get_logger(__name__)


class RegimeGuard:
    """
    Calculates a regime score based on sector volatility.
    """

    def __init__(self, scoring: ScoringConfig):
        self.scoring = scoring

    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """Calculates a regime score based on sector volatility. Prefers `signal.sector_vol` and falls back to dataframe column."""
        sector_vol = getattr(signal, "sector_vol", None)
        if sector_vol is None and "sector_vol" in full_df.columns:
            sector_vol = full_df.iloc[current_index]["sector_vol"]

        if sector_vol is None or pd.isna(sector_vol):
            return 0.0

        score = linear_score(
            value=sector_vol,
            min_val=self.scoring.regime_score_min_volatility_pct,
            max_val=self.scoring.regime_score_max_volatility_pct,
        )

        log.debug(
            f"Regime score for signal on {full_df.index[current_index].date()}: {score:.2f} "
            f"(Sector Vol: {sector_vol:.2f}%)"
        )

        return score
