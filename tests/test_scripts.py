import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from scripts.train_regime_model import train_and_save_model
from praxis_engine.core.models import Config, MarketDataConfig, DataConfig, RegimeModelConfig

@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """Provides a mock Config object for testing."""
    config = MagicMock(spec=Config)

    config.market_data = MagicMock(spec=MarketDataConfig)
    config.market_data.cache_dir = str(tmp_path)
    config.market_data.index_ticker = "^NSEI"
    config.market_data.vix_ticker = "^INDIAVIX"
    config.market_data.training_start_date = "2020-01-01"

    config.data = MagicMock(spec=DataConfig)
    config.data.end_date = "2021-01-01"

    config.regime_model = MagicMock(spec=RegimeModelConfig)
    config.regime_model.model_path = str(tmp_path / "regime_model.joblib")
    config.regime_model.volatility_threshold_percentile = 0.75

    return config

def create_dummy_market_data() -> dict[str, pd.DataFrame]:
    """Creates a dummy market data dictionary for mocking."""
    dates = pd.to_datetime(pd.date_range(start="2020-01-01", end="2021-01-01", freq="D"))
    close_prices = 12000 + np.random.randn(len(dates)).cumsum()
    nifty_data = pd.DataFrame({"Close": close_prices}, index=dates)
    vix_data = pd.DataFrame({"Close": 15.5}, index=dates)
    return {"^NSEI": nifty_data, "^INDIAVIX": vix_data}

def create_dummy_features() -> pd.DataFrame:
    """Creates a dummy features DataFrame for mocking."""
    dates = pd.to_datetime(pd.date_range(start="2020-01-01", end="2021-01-01", freq="D"))
    return pd.DataFrame({"nifty_vs_200ma": 1.05}, index=dates)

@patch('scripts.train_regime_model.calculate_market_features', return_value=create_dummy_features())
@patch('scripts.train_regime_model.MarketDataService.get_market_data', return_value=create_dummy_market_data())
def test_train_and_save_model_creates_file(
    mock_get_market_data: MagicMock,
    mock_calculate_features: MagicMock,
    mock_config: Config
):
    """
    Tests that the train_and_save_model function runs successfully
    and creates a model file in the specified directory.
    """
    # Act
    success = train_and_save_model(mock_config)

    # Assert
    assert success is True

    mock_get_market_data.assert_called_once()
    mock_calculate_features.assert_called_once()

    model_path = Path(mock_config.regime_model.model_path)
    assert model_path.exists()
    assert model_path.is_file()
