"""
This service is responsible for loading and serving the trained market regime model.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List

import joblib
import pandas as pd

from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class RegimeModelService:
    """
    A resilient, fallback-aware service for the market regime model.
    """

    def __init__(self, model_path: str = "results/regime_model.joblib"):
        """
        Initializes the service and loads the model if it exists.

        Args:
            model_path: The path to the saved regime model file.
        """
        self.model_path = Path(model_path)
        self.model: Optional[Any] = None
        self.feature_columns: Optional[List[str]] = None

        if self.model_path.exists():
            try:
                log.info(f"Loading regime model from: {self.model_path}")
                model_data: Dict[str, Any] = joblib.load(self.model_path)
                self.model = model_data.get("model")
                self.feature_columns = model_data.get("feature_columns")
                if not self.model or not self.feature_columns:
                    log.error("Model file is corrupt or missing 'model' or 'feature_columns' keys.")
                    self.model = None # Ensure model is None if file is invalid
            except Exception as e:
                log.error(f"Failed to load regime model from {self.model_path}: {e}")
                self.model = None
        else:
            log.warning(
                f"Regime model not found at {self.model_path}. "
                "RegimeGuard will fall back to a neutral score of 1.0."
            )

    def predict_proba(self, features_df: pd.DataFrame) -> Optional[float]:
        """
        Predicts the probability of a "good" regime (class 1).

        Args:
            features_df: A DataFrame containing the necessary features for prediction.
                         Should contain a single row of the latest features.

        Returns:
            The probability of class 1 (good regime), or 1.0 if the model is not loaded.
            Returns None if prediction fails.
        """
        if self.model is None or self.feature_columns is None:
            return 1.0  # Fallback to neutral score

        if features_df.empty:
            log.warning("Cannot predict regime on empty features DataFrame.")
            return None

        # Ensure all required columns are present
        if not all(col in features_df.columns for col in self.feature_columns):
            log.error(f"Missing required feature columns for regime model prediction.")
            return None

        # Reorder columns to match training order and handle potential NaNs
        latest_features = features_df[self.feature_columns].iloc[-1:]
        if latest_features.isnull().values.any():
            log.warning("NaN values found in features for regime prediction. Cannot predict.")
            return None

        try:
            # predict_proba returns probabilities for [class 0, class 1]
            probabilities = self.model.predict_proba(latest_features)
            good_regime_proba = probabilities[0, 1]
            return good_regime_proba
        except Exception as e:
            log.error(f"Error during regime model prediction: {e}")
            return None
