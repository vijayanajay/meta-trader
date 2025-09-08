"""
A guard to calculate a score based on market regime using a trained model,
with a fallback to sector volatility.
"""
import pandas as pd

from praxis_engine.core.models import Signal, ScoringConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.guards.decorators import normalize_guard_args
from praxis_engine.services.regime_model_service import RegimeModelService
from praxis_engine.core.guards.scoring_utils import linear_score

log = get_logger(__name__)


class RegimeGuard:
    """
    Calculates a regime score.
    It first attempts to use a pre-trained classification model.
    If the model is not available or returns a neutral score, it falls back
    to a simple score based on the stock's sector volatility.
    """

    def __init__(self, scoring: ScoringConfig, regime_model_service: RegimeModelService):
        self.scoring = scoring
        self.regime_model_service = regime_model_service
        # The features the model was trained on. Must match `train_regime_model.py`.
        self.model_features = ["nifty_vs_200ma", "vix_level", "vix_roc_10d"]

    @normalize_guard_args
    def validate(self, full_df: pd.DataFrame, current_index: int, signal: Signal) -> float:
        """
        Calculates a regime score, using the model first and falling back to sector vol.
        """
        # --- Model-based Score ---
        # Check which model features are available in the dataframe
        available_features = [f for f in self.model_features if f in full_df.columns]

        if len(available_features) != len(self.model_features):
            log.warning(
                f"Missing one or more market feature columns for {full_df.index[current_index].date()}. "
                "Defaulting to neutral model score."
            )
            model_score = 1.0
        else:
            current_day_features = full_df.iloc[[current_index]][self.model_features]
            if current_day_features.isnull().values.any():
                log.warning(
                    f"One or more market features are NaN for {full_df.index[current_index].date()}. "
                    "Defaulting to neutral model score."
                )
                model_score = 1.0
            else:
                model_score = self.regime_model_service.predict_proba(current_day_features)

        # --- Fallback Logic ---
        # If the model gives a neutral score (e.g., it's not loaded), use the fallback.
        if model_score == 1.0:
            log.debug("Regime model returned neutral score. Using sector volatility fallback.")
            fallback_score = self._calculate_fallback_score(signal)
            log.debug(
                f"Regime fallback score for signal on {full_df.index[current_index].date()}: {fallback_score:.2f}"
            )
            return fallback_score

        log.debug(
            f"Regime model score for signal on {full_df.index[current_index].date()}: {model_score:.2f}"
        )
        return model_score

    def _calculate_fallback_score(self, signal: Signal) -> float:
        """
        Calculates a score based on sector volatility. Lower volatility is better.
        """
        sector_vol = signal.sector_vol
        min_vol_for_scoring = self.scoring.regime_score_max_volatility_pct # Lower is better, so this is the "good" end
        max_vol_for_scoring = self.scoring.regime_score_min_volatility_pct # This is the "bad" end

        # We want to score lower volatility higher.
        # e.g., if vol < 10 (min_vol_for_scoring), score is 1.0.
        # if vol > 25 (max_vol_for_scoring), score is 0.0.
        # The linear_score function handles this inversion if min_val > max_val.
        return linear_score(sector_vol, min_val=max_vol_for_scoring, max_val=min_vol_for_scoring)
