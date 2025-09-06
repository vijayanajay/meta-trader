"""
A guard to calculate a score based on market regime using a trained model.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.decorators import normalize_guard_args
from praxis_engine.services.regime_model_service import RegimeModelService

log = get_logger(__name__)


class RegimeGuard:
    """
    Calculates a regime score using a pre-trained classification model.
    """

    def __init__(self, scoring: ScoringConfig, regime_model_service: RegimeModelService):
        self.scoring = scoring
        self.regime_model_service = regime_model_service

    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """
        Calculates a regime score by predicting the probability of a "good" regime.
        """
        # The Orchestrator should have joined the features into the full_df.
        # We pass the full dataframe up to the current point to the service.
        features_for_prediction = full_df.iloc[0 : current_index + 1]

        score = self.regime_model_service.predict_proba(features_for_prediction)

        if score is None:
            log.error(
                f"Regime model prediction failed for signal on {full_df.index[current_index].date()}. "
                "Returning score of 0.0"
            )
            return 0.0

        log.debug(
            f"Regime score for signal on {full_df.index[current_index].date()}: {score:.2f}"
        )

        return score
