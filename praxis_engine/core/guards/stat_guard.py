"""
A guard to calculate a score for the statistical validity of a signal.
"""
import math
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig, StrategyParamsConfig
from praxis_engine.core.statistics import adf_test, hurst_exponent
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score
from praxis_engine.core.guards.decorators import normalize_guard_args

log = get_logger(__name__)


class StatGuard:
    """
    Calculates a statistical score based on ADF and Hurst tests.
    """

    def __init__(self, scoring: ScoringConfig, params: StrategyParamsConfig):
        self.scoring = scoring
        self.params = params

    # impure
    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """Calculates a statistical score based on precomputed ADF/Hurst with safe fallbacks."""
        hurst_col = f"HURST_{self.params.hurst_length}"
        adf_col = f"ADF_{self.params.hurst_length}"

        adf_p_value = None
        hurst = None

        # Try using precomputed ADF
        if adf_col in full_df.columns:
            try:
                adf_p_value = full_df.iloc[current_index][adf_col]
            except (IndexError, KeyError):
                adf_p_value = None

        # Fallback: compute ADF on returns
        if adf_p_value is None or pd.isna(adf_p_value):
            try:
                returns = full_df["Close"].iloc[: current_index + 1].pct_change().dropna()
                if len(returns) >= max(1, self.params.hurst_length - 1):
                    adf_p_value = adf_test(returns)
            except (IndexError, KeyError, ValueError) as e:
                log.debug(f"ADF fallback computation failed: {e}")
                adf_p_value = None

        # Try using precomputed Hurst
        if hurst_col in full_df.columns:
            try:
                hurst = full_df.iloc[current_index][hurst_col]
            except (IndexError, KeyError):
                hurst = None

        # Fallback: compute Hurst from price history
        if hurst is None or pd.isna(hurst):
            try:
                prices = full_df["Close"].iloc[: current_index + 1]
                if len(prices) >= self.params.hurst_length:
                    hurst = hurst_exponent(prices)
            except (IndexError, KeyError, ValueError) as e:
                log.debug(f"Hurst fallback computation failed: {e}")
                hurst = None

        if adf_p_value is None or pd.isna(adf_p_value):
            log.warning(f"ADF p-value unavailable for signal on {full_df.index[current_index].date()}.")
            adf_score = 0.0
        else:
            adf_score = linear_score(
                value=adf_p_value,
                min_val=self.scoring.adf_score_min_pvalue,
                max_val=self.scoring.adf_score_max_pvalue,
            )

        if hurst is None or pd.isna(hurst):
            log.warning(f"Hurst exponent unavailable for signal on {full_df.index[current_index].date()}.")
            hurst_score = 0.0
        else:
            hurst_score = linear_score(
                value=hurst,
                min_val=self.scoring.hurst_score_min_h,
                max_val=self.scoring.hurst_score_max_h,
            )

        final_score = math.sqrt(adf_score * hurst_score)

        log.debug(
            f"Stat score for signal on {full_df.index[current_index].date()}: {final_score:.2f} "
            f"(ADF p-value: {f'{adf_p_value:.4f}' if adf_p_value is not None else 'N/A'}, "
            f"Hurst: {f'{hurst:.2f}' if hurst is not None else 'N/A'})"
        )

        return final_score
