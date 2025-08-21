"""
Service for loading and validating application configuration.
"""
import configparser
from typing import Dict, Any, List
from dotenv import dotenv_values
from pathlib import Path

from src.core.models import Config, LLMSettings, AppSettings

__all__ = ["ConfigService"]


class ConfigService:
    """
    Handles loading of configuration from .env and config.ini files.
    """
    def __init__(self, config_path: str = "config.ini", env_path: str = ".env"):
        self._config_path = Path(config_path)
        self._env_path = Path(env_path)

    # impure
    def load_config(self) -> Config:
        """
        Loads configuration from files, validates them using Pydantic models,
        and returns a unified Config object.

        Returns:
            Config: The validated application configuration.

        Raises:
            FileNotFoundError: If the config.ini file is not found.
            KeyError: If a required setting is missing from the configuration files.
        """
        if not self._config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {self._config_path}")

        # Load .env file for secrets
        env_config: Dict[str, Any] = dotenv_values(self._env_path)

        # Load .ini file for application settings
        parser = configparser.ConfigParser()
        parser.read(self._config_path)

        # Extract sections
        settings = parser['settings']
        data_settings = parser['data']
        strategy_settings = parser['strategy']

        # Parse and type-cast application settings
        app_settings_data = {
            "tickers": [ticker.strip() for ticker in settings.get("tickers", "").split(",")],
            "iterations": settings.getint("iterations", 10),
            "data_dir": settings.get("data_dir", "data"),
            "results_dir": settings.get("results_dir", "results"),
            "run_state_file": settings.get("run_state_file", "run_state.json"),
            "train_split_ratio": data_settings.getfloat("train_split_ratio", 0.8),
            "data_period": data_settings.get("data_period", "10y"),
            "baseline_strategy_name": strategy_settings.get("baseline_strategy_name", "SMA_Crossover"),
            "sharpe_threshold": strategy_settings.getfloat("sharpe_threshold", 0.1),
        }

        # Validate using Pydantic models
        llm_settings = LLMSettings.model_validate(env_config)
        app_settings = AppSettings.model_validate(app_settings_data)

        return Config(llm=llm_settings, app=app_settings)
