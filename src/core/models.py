"""
Pydantic models for the application's configuration and data structures.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any

__all__ = [
    "LLMSettings",
    "AppSettings",
    "Config",
    "Indicator",
    "StrategyDefinition",
    "TradeSummary",
    "PerformanceReport",
]


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


# ==============================================================================
# Models for Strategy Definition and Performance Reporting
# ==============================================================================


class Indicator(BaseModel):
    """
    Defines a single technical indicator to be calculated.
    """
    name: str
    function: str
    params: Dict[str, Any]


class StrategyDefinition(BaseModel):
    """
    Defines the structure for an LLM-proposed trading strategy.
    This is the JSON schema the LLM is expected to return.
    """
    strategy_name: str
    indicators: List[Indicator]
    buy_condition: str
    sell_condition: str


class TradeSummary(BaseModel):
    """
    The information-dense statistical summary of trades from a backtest,
    as specified in FR4.
    """
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    max_consecutive_losses: int
    avg_trade_duration_bars: int


class PerformanceReport(BaseModel):
    """
    A comprehensive report object containing all information about a single
    backtest iteration. This is the primary object appended to the history
    and fed back to the LLM.
    """
    strategy: StrategyDefinition
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    annual_return_pct: float
    trade_summary: TradeSummary
