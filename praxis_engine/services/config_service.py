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

        return Config.model_validate(config_dict)
