import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression

from praxis_engine.services.regime_model_service import RegimeModelService


class TestRegimeModelService(unittest.TestCase):

    def setUp(self):
        self.test_model_path = "test_regime_model.joblib"
        # Clean up any old test model file
        if Path(self.test_model_path).exists():
            Path(self.test_model_path).unlink()

    def tearDown(self):
        # Clean up test model file after tests
        if Path(self.test_model_path).exists():
            Path(self.test_model_path).unlink()

    def test_init_model_not_found(self):
        """Test that the service initializes gracefully when the model file does not exist."""
        with patch("praxis_engine.services.regime_model_service.log.warning") as mock_log_warning:
            service = RegimeModelService(model_path="non_existent_model.joblib")
            self.assertIsNone(service.model)
            self.assertIsNone(service.feature_columns)
            mock_log_warning.assert_called_once()
            self.assertIn("Regime model not found", mock_log_warning.call_args[0][0])

    def test_predict_proba_no_model_fallback(self):
        """Test that predict_proba returns 1.0 when no model is loaded."""
        service = RegimeModelService(model_path="non_existent_model.joblib")
        features_df = pd.DataFrame([{"feature1": 1, "feature2": 2}])

        proba = service.predict_proba(features_df)
        self.assertEqual(proba, 1.0)

    @patch("joblib.load")
    def test_init_model_loads_successfully(self, mock_joblib_load):
        """Test successful loading of a valid model file."""
        # Arrange
        mock_model = MagicMock()
        mock_feature_columns = ["feature1", "feature2"]
        mock_joblib_load.return_value = {
            "model": mock_model,
            "feature_columns": mock_feature_columns,
        }

        with patch("pathlib.Path.exists", return_value=True):
            # Act
            service = RegimeModelService(model_path=self.test_model_path)

            # Assert
            self.assertIsNotNone(service.model)
            self.assertEqual(service.model, mock_model)
            self.assertEqual(service.feature_columns, mock_feature_columns)
            mock_joblib_load.assert_called_once_with(Path(self.test_model_path))

    def test_predict_proba_with_loaded_model(self):
        """Test that predict_proba calls the loaded model correctly."""
        # Arrange
        # Use a real, simple model that can be pickled
        real_model = LogisticRegression()
        feature_cols = ["f1", "f2"]
        # Train it on a dummy DataFrame so it has feature names
        train_df = pd.DataFrame([[1, 2], [3, 4]], columns=feature_cols)
        real_model.fit(train_df, [0, 1])

        model_data = {"model": real_model, "feature_columns": feature_cols}
        joblib.dump(model_data, self.test_model_path)

        service = RegimeModelService(model_path=self.test_model_path)

        features_df = pd.DataFrame([{"f1": 1, "f2": 2}])

        # Act
        proba = service.predict_proba(features_df)

        # Assert
        self.assertIsInstance(proba, float)
        self.assertGreaterEqual(proba, 0.0)
        self.assertLessEqual(proba, 1.0)
        # Check that the probability for class 1 is returned
        expected_proba = real_model.predict_proba(features_df[feature_cols])
        self.assertAlmostEqual(proba, expected_proba[0, 1])

    def test_predict_proba_handles_nan_features(self):
        """Test that predict_proba returns None if features contain NaN."""
        real_model = LogisticRegression()
        feature_cols = ["f1", "f2"]
        model_data = {"model": real_model, "feature_columns": feature_cols}
        joblib.dump(model_data, self.test_model_path)

        service = RegimeModelService(model_path=self.test_model_path)
        features_df = pd.DataFrame([{"f1": 1, "f2": None}])

        with patch("praxis_engine.services.regime_model_service.log.warning") as mock_log_warning:
            proba = service.predict_proba(features_df)
            self.assertIsNone(proba)
            mock_log_warning.assert_called_once_with("NaN values found in features for regime prediction. Cannot predict.")

    def test_predict_proba_handles_missing_columns(self):
        """Test that predict_proba returns None if feature columns are missing."""
        real_model = LogisticRegression()
        feature_cols = ["f1", "f2"]
        model_data = {"model": real_model, "feature_columns": feature_cols}
        joblib.dump(model_data, self.test_model_path)

        service = RegimeModelService(model_path=self.test_model_path)
        features_df = pd.DataFrame([{"f1": 1}]) # Missing 'f2'

        with patch("praxis_engine.services.regime_model_service.log.error") as mock_log_error:
            proba = service.predict_proba(features_df)
            self.assertIsNone(proba)
            mock_log_error.assert_called_once_with("Missing required feature columns for regime model prediction.")
