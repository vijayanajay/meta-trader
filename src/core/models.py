"""
Pydantic models for the application's configuration and data structures.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

__all__ = [
    "LLMSettings",
    "AppSettings",
    "Config",
    "Indicator",
    "StrategyDefinition",
    "TradeSummary",
    "PerformanceReport",
    "RunState",
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


class BacktestSettings(BaseModel):
    """
    Settings for the backtesting engine.
    """
    cash: int
    commission: float
    trade_size: float


class Config(BaseModel):
    """
    The main configuration object, aggregating all settings.
    """
    llm: LLMSettings
    app: AppSettings
    backtest: BacktestSettings


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
    performance: "PerformanceMetrics"
    trade_summary: TradeSummary
    is_pruned: bool = False
    next_strategy_suggestion: StrategyDefinition | None = None

    @classmethod
    def create_pruned(cls, strategy_def: StrategyDefinition) -> "PerformanceReport":
        """Factory method to create a report for a pruned/failed iteration."""
        return cls(
            strategy=strategy_def,
            performance=PerformanceMetrics(
                sharpe_ratio=-999.0,
                sortino_ratio=-999.0,
                max_drawdown_pct=-999.0,
                annual_return_pct=-999.0,
            ),
            trade_summary=TradeSummary(
                total_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                avg_win_pct=0.0,
                avg_loss_pct=0.0,
                max_consecutive_losses=0,
                avg_trade_duration_bars=0,
            ),
            is_pruned=True,
        )


class PerformanceMetrics(BaseModel):
    """
    Holds the key performance indicators from a backtest run.
    Handles cases where metrics are undefined by defaulting to 0.0.
    """
    sharpe_ratio: Optional[float] = 0.0
    sortino_ratio: Optional[float] = 0.0
    max_drawdown_pct: Optional[float] = 0.0
    annual_return_pct: Optional[float] = 0.0


class RunState(BaseModel):
    """
    Represents the state of a single optimization run for a ticker,
    allowing the process to be resumed.
    """
    iteration_number: int
    history: List[PerformanceReport]
