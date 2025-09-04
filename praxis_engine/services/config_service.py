import configparser
from typing import Dict, Any
import ast

from praxis_engine.core.models import Config

class ConfigService:
    def __init__(self, path: str = "config.ini"):
        self.path = path

    def load_config(self) -> Config:
        """
        Loads the configuration from a .ini file and validates it using Pydantic.

        Returns:
            A validated Config object.
        """
        parser = configparser.ConfigParser()
        if not parser.read(self.path):
            raise FileNotFoundError(f"Configuration file not found at path: {self.path}")

        config_dict: Dict[str, Dict[str, Any]] = {}
        for section in parser.sections():
            config_dict[section] = {}
            for key, value in parser.items(section):
                try:
                    # Safely evaluate the value to handle dicts, lists, numbers, etc.
                    config_dict[section][key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    # If it's not a literal, treat it as a string
                    config_dict[section][key] = value

        # Special handling for stocks_to_backtest to ensure it's a list
        if 'data' in config_dict and 'stocks_to_backtest' in config_dict['data']:
            stocks = config_dict['data']['stocks_to_backtest']
            if isinstance(stocks, str):
                config_dict['data']['stocks_to_backtest'] = [s.strip() for s in stocks.split(',')]

        return Config.model_validate(config_dict)
