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

    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """
        Calculates a statistical score based on pre-computed ADF and Hurst values.
        This method relies on the Orchestrator having run precompute_indicators.
        """
        hurst_col = f"HURST_{self.params.hurst_length}"
        adf_col = f"ADF_{self.params.hurst_length}"

        adf_p_value = None
        hurst = None

        if adf_col in full_df.columns:
            adf_p_value = full_df.iloc[current_index].get(adf_col)

        if hurst_col in full_df.columns:
            hurst = full_df.iloc[current_index].get(hurst_col)

        if adf_p_value is None or pd.isna(adf_p_value):
            log.debug(f"ADF p-value not found in pre-computed data for {full_df.index[current_index].date()}.")
            adf_score = 0.0
        else:
            adf_score = linear_score(
                value=adf_p_value,
                min_val=self.scoring.adf_score_min_pvalue,
                max_val=self.scoring.adf_score_max_pvalue,
            )

        if hurst is None or pd.isna(hurst):
            log.debug(f"Hurst exponent not found in pre-computed data for {full_df.index[current_index].date()}.")
            hurst_score = 0.0
        else:
            hurst_score = linear_score(
                value=hurst,
                min_val=self.scoring.hurst_score_min_h,
                max_val=self.scoring.hurst_score_max_h,
            )

        # The geometric mean is used to ensure both conditions must be met to get a good score.
        # If either score is 0, the final score will be 0.
        final_score = math.sqrt(adf_score * hurst_score)

        log.debug(
            f"Stat score for signal on {full_df.index[current_index].date()}: {final_score:.2f} "
            f"(ADF p-value: {f'{adf_p_value:.4f}' if adf_p_value is not None else 'N/A'}, "
            f"Hurst: {f'{hurst:.2f}' if hurst is not None else 'N/A'})"
        )

        return final_score
