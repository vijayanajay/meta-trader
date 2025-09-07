import joblib
from pathlib import Path
from typing import Optional, Any
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

# impure
class RegimeModelService:
    """
    A resilient, fallback-aware service for the market regime model.
    It attempts to load a model and falls back to a neutral behavior if the model is missing.
    """

    def __init__(self, model_path: str):
        """
        Initializes the service and loads the model if it exists.

        Args:
            model_path: The path to the saved regime model file.
        """
        self.model: Optional[Any] = None
        try:
            # [H-9] Catch specific, anticipated exceptions.
            self.model = joblib.load(model_path)
            log.info(f"Regime model loaded successfully from {model_path}")
        except FileNotFoundError:
            # [H-9] Failures must be logged with context and handled gracefully.
            log.warning(
                f"Regime model file not found at {model_path}. "
                "The service will fall back to a neutral regime prediction (1.0)."
            )
            # self.model is already None, no need to set it again.
        except Exception as e:
            # Catch other potential errors during file loading (e.g., corrupt file)
            log.error(f"An unexpected error occurred while loading model from {model_path}: {e}")
            self.model = None # Ensure model is None on other failures.


    def predict_proba(self, features: Any) -> float:
        """
        Predicts the probability of a "good" regime.

        If the model is not loaded, it returns a neutral probability of 1.0.
        Otherwise, it uses the model to predict and returns the probability for the "good" class.

        Args:
            features: The input features for the model.

        Returns:
            The probability of a "good" regime (class 1), which is assumed to be at index 1.
        """
        if self.model is None:
            return 1.0

        try:
            # predict_proba usually returns an array of shape (n_samples, n_classes)
            # e.g., [[prob_class_0, prob_class_1]] for a single sample.
            probabilities = self.model.predict_proba(features)
            # Assuming "good regime" is class 1.
            return probabilities[0, 1]
        except Exception as e:
            log.error(f"Error during regime model prediction: {e}")
            # Fallback to a neutral score on prediction failure.
            return 1.0
