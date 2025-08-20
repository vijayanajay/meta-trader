from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["StrategyDefinition", "RiskManagement", "IterationReport"]


class StrategyDefinition(BaseModel):
    """Defines the indicators and logic for a trading strategy."""

    rationale: str = Field(..., description="The LLM's reasoning for proposing this strategy.")
    indicators: list[dict[str, Any]]
    buy_signal: str
    sell_signal: str


class RiskManagement(BaseModel):
    """Defines risk management rules, like stop-loss and take-profit."""

    stop_loss_pct: float | None = Field(None, description="Stop-loss percentage, e.g., 0.10 for 10%.")
    take_profit_pct: float | None = Field(None, description="Take-profit percentage, e.g., 0.25 for 25%.")


class IterationReport(BaseModel):
    """A comprehensive report of a single strategy backtest iteration."""

    iteration: int
    strategy: StrategyDefinition
    risk_management: RiskManagement | None = None
    status: Literal["success", "failure"] = "success"
    error_message: str | None = None

    # Core backtest metrics from backtesting.py
    start_date: str = Field(..., alias="Start")
    end_date: str = Field(..., alias="End")
    duration: str = Field(..., alias="Duration")
    exposure_time_pct: float = Field(..., alias="Exposure Time [%]")
    equity_final: float = Field(..., alias="Equity Final [$]")
    equity_peak: float = Field(..., alias="Equity Peak [$]")
    return_pct: float = Field(..., alias="Return [%]")
    buy_and_hold_return_pct: float = Field(..., alias="Buy & Hold Return [%]")
    return_ann_pct: float = Field(..., alias="Return (Ann.) [%]")
    volatility_ann_pct: float = Field(..., alias="Volatility (Ann.) [%]")
    sharpe_ratio: float = Field(..., alias="Sharpe Ratio")
    sortino_ratio: float = Field(..., alias="Sortino Ratio")
    calmar_ratio: float = Field(..., alias="Calmar Ratio")
    max_drawdown_pct: float = Field(..., alias="Max. Drawdown [%]")
    avg_drawdown_pct: float = Field(..., alias="Avg. Drawdown [%]")
    max_drawdown_duration: int = Field(..., alias="Max. Drawdown Duration")
    avg_drawdown_duration: int = Field(..., alias="Avg. Drawdown Duration")
    num_trades: int = Field(..., alias="# Trades")
    win_rate_pct: float = Field(..., alias="Win Rate [%]")
    best_trade_pct: float = Field(..., alias="Best Trade [%]")
    worst_trade_pct: float = Field(..., alias="Worst Trade [%]")
    avg_trade_pct: float = Field(..., alias="Avg. Trade [%]")
    max_trade_duration: int = Field(..., alias="Max. Trade Duration")
    avg_trade_duration: int = Field(..., alias="Avg. Trade Duration")
    profit_factor: float = Field(..., alias="Profit Factor")
    expectancy_pct: float = Field(..., alias="Expectancy [%]")
    sqn: float = Field(..., alias="SQN")

    # The custom score for ranking strategies
    edge_score: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
