import joblib
import numpy as np
from unittest.mock import patch
from pathlib import Path
import pytest

from praxis_engine.services.regime_model_service import RegimeModelService

# A dummy model class for testing successful prediction
class DummyModel:
    def predict_proba(self, features):
        return np.array([[0.2, 0.8]])

# A dummy model class for testing prediction failures
class FailingDummyModel:
    def predict_proba(self, features):
        raise ValueError("Prediction failed!")

@pytest.fixture
def model_path(tmp_path: Path) -> str:
    """A fixture to create a temporary model file path."""
    return str(tmp_path / "test_model.joblib")

def test_init_model_not_found():
    """
    Test that the service initializes gracefully when the model file does not exist.
    """
    with patch("praxis_engine.services.regime_model_service.log.warning") as mock_log_warning:
        service = RegimeModelService(model_path="non_existent_model.joblib")
        assert service.model is None
        mock_log_warning.assert_called_once()
        assert "Regime model file not found" in mock_log_warning.call_args[0][0]

def test_predict_proba_no_model_fallback():
    """
    Test that predict_proba returns a neutral score of 1.0 when no model is loaded.
    """
    service = RegimeModelService(model_path="non_existent_model.joblib")
    proba = service.predict_proba(features=[[1, 2]])
    assert proba == 1.0

def test_init_model_loads_successfully(model_path: str):
    """Test that the service loads a model from a file successfully."""
    dummy_model = DummyModel()
    joblib.dump(dummy_model, model_path)

    with patch("praxis_engine.services.regime_model_service.log.info") as mock_log_info:
        service = RegimeModelService(model_path)
        assert service.model is not None
        assert isinstance(service.model, DummyModel)
        mock_log_info.assert_called_once()
        assert "Regime model loaded successfully" in mock_log_info.call_args[0][0]

def test_predict_proba_with_loaded_model(model_path: str):
    """Test that predict_proba uses the loaded model and returns the correct probability."""
    dummy_model = DummyModel()
    joblib.dump(dummy_model, model_path)

    service = RegimeModelService(model_path)

    # The features can be anything since the dummy model ignores them
    features = [[10, 20]]
    proba = service.predict_proba(features)

    # Assert that the probability for the "good" class (index 1) is returned
    assert proba == 0.8

def test_predict_proba_handles_prediction_error(model_path: str):
    """
    Test that predict_proba falls back to 1.0 if the model's predict_proba method fails.
    """
    failing_model = FailingDummyModel()
    joblib.dump(failing_model, model_path)

    service = RegimeModelService(model_path)

    with patch("praxis_engine.services.regime_model_service.log.error") as mock_log_error:
        proba = service.predict_proba(features=[[1, 2]])
        assert proba == 1.0
        mock_log_error.assert_called_once()
        assert "Error during regime model prediction" in mock_log_error.call_args[0][0]
