"""
A guard to calculate a score for the statistical validity of a signal.
"""
import math
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig, StrategyParamsConfig
from praxis_engine.core.statistics import adf_test, hurst_exponent
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.scoring_utils import linear_score

log = get_logger(__name__)


class StatGuard:
    """
    Calculates a statistical score based on ADF and Hurst tests.
    """

    def __init__(self, scoring: ScoringConfig, params: StrategyParamsConfig):
        self.scoring = scoring
        self.params = params

    # impure
    def validate(self, df: pd.DataFrame, signal: Signal) -> float:
        """
        Calculates a score based on mean-reverting characteristics.
        The final score is the geometric mean of the ADF and Hurst scores.
        """
        price_series = df["Close"]
        adf_p_value = adf_test(price_series.pct_change().dropna())
        hurst = hurst_exponent(price_series)

        if adf_p_value is None:
            log.warning(f"ADF test failed for signal on {df.index[-1].date()}. Could not compute p-value.")
            adf_score = 0.0
        else:
            adf_score = linear_score(
                value=adf_p_value,
                min_val=self.scoring.adf_score_min_pvalue,
                max_val=self.scoring.adf_score_max_pvalue,
            )

        if hurst is None:
            log.warning(f"Hurst exponent calculation failed for signal on {df.index[-1].date()}.")
            hurst_score = 0.0
        else:
            hurst_score = linear_score(
                value=hurst,
                min_val=self.scoring.hurst_score_min_h,
                max_val=self.scoring.hurst_score_max_h,
            )

        # Geometric mean of the two scores
        final_score = math.sqrt(adf_score * hurst_score)

        log.debug(
            f"Stat score for signal on {df.index[-1].date()}: {final_score:.2f} "
            f"(ADF p-value: {f'{adf_p_value:.4f}' if adf_p_value is not None else 'N/A'}, "
            f"Hurst: {f'{hurst:.2f}' if hurst is not None else 'N/A'})"
        )

        return final_score
