"""
Pydantic models for the application's configuration and data structures.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List

__all__ = ["LLMSettings", "AppSettings", "Config"]


class LLMSettings(BaseModel):
    """
    Settings for the LLM provider, loaded from environment variables.
    """
    provider: str = Field(..., alias='LLM_PROVIDER')
    openai_api_key: str = Field("your_openai_api_key_here", alias='OPENAI_API_KEY')
    openai_model: str = Field("gpt-4-turbo", alias='OPENAI_MODEL')
    openrouter_api_key: str = Field(..., alias='OPENROUTER_API_KEY')
    openrouter_model: str = Field("moonshotai/kimi-k2:free", alias='OPENROUTER_MODEL')
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", alias='OPENROUTER_BASE_URL')

    model_config = ConfigDict(populate_by_name=True)


class AppSettings(BaseModel):
    """
    Application settings, loaded from config.ini.
    """
    tickers: List[str]
    iterations: int
    data_dir: str
    results_dir: str
    run_state_file: str
    train_split_ratio: float
    data_period: str
    baseline_strategy_name: str
    sharpe_threshold: float


class Config(BaseModel):
    """
    The main configuration object, aggregating all settings.
    """
    llm: LLMSettings
    app: AppSettings
