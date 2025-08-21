"""
Unit tests for the ConfigService.
"""
import pytest
from pydantic import ValidationError
from pathlib import Path

from services.config_service import ConfigService

# A minimal valid .env content for testing
MINIMAL_ENV_CONTENT = """
LLM_PROVIDER="openrouter"
OPENROUTER_API_KEY="fake_key_for_testing"
"""

# A minimal valid config.ini content for testing
MINIMAL_CONFIG_INI_CONTENT = """
[settings]
tickers = TICK1, TICK2
iterations = 5
data_dir = /tmp/data
results_dir = /tmp/results
run_state_file = state.json

[data]
train_split_ratio = 0.9
data_period = 5y

[strategy]
baseline_strategy_name = Test_Strategy
sharpe_threshold = 0.5
"""


def test_load_config_success(tmp_path: Path):
    """
    Tests that a valid configuration is loaded correctly.
    """
    # Create temporary config files
    env_file = tmp_path / ".env"
    env_file.write_text(MINIMAL_ENV_CONTENT)

    config_file = tmp_path / "config.ini"
    config_file.write_text(MINIMAL_CONFIG_INI_CONTENT)

    # Instantiate the service and load config
    service = ConfigService(config_path=str(config_file), env_path=str(env_file))
    config = service.load_config()

    # Assert LLM settings
    assert config.llm.provider == "openrouter"
    assert config.llm.openrouter_api_key == "fake_key_for_testing"

    # Assert App settings
    assert config.app.tickers == ["TICK1", "TICK2"]
    assert config.app.iterations == 5
    assert config.app.train_split_ratio == 0.9
    assert config.app.baseline_strategy_name == "Test_Strategy"
    assert config.app.sharpe_threshold == 0.5


def test_load_config_missing_ini_file():
    """
    Tests that a FileNotFoundError is raised if config.ini is missing.
    """
    service = ConfigService(config_path="non_existent_file.ini")
    with pytest.raises(FileNotFoundError):
        service.load_config()


def test_load_config_missing_env_file_raises_validation_error(tmp_path: Path):
    """
    Tests that a Pydantic ValidationError is raised if a required field
    from the .env file is missing.
    """
    # Create only the config.ini file
    config_file = tmp_path / "config.ini"
    config_file.write_text(MINIMAL_CONFIG_INI_CONTENT)

    # Point to a non-existent .env file
    service = ConfigService(config_path=str(config_file), env_path=str(tmp_path / "non_existent.env"))

    with pytest.raises(ValidationError) as excinfo:
        service.load_config()

    # Check that the error is about the missing openrouter_api_key
    assert "OPENROUTER_API_KEY" in str(excinfo.value)


def test_load_config_missing_section_in_ini_raises_key_error(tmp_path: Path):
    """
    Tests that a KeyError is raised if a required section is missing from config.ini.
    """
    # Create a config.ini file that's missing the [strategy] section
    invalid_config_content = """
    [settings]
    tickers = A, B
    iterations = 1
    data_dir = /d
    results_dir = /r
    run_state_file = s.json

    [data]
    train_split_ratio = 0.8
    data_period = 1y
    """
    config_file = tmp_path / "config.ini"
    config_file.write_text(invalid_config_content)

    env_file = tmp_path / ".env"
    env_file.write_text(MINIMAL_ENV_CONTENT)

    service = ConfigService(config_path=str(config_file), env_path=str(env_file))

    with pytest.raises(KeyError):
        service.load_config()
