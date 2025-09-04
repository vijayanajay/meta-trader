"""
Pydantic models for the application.
"""
import pandas as pd
from pydantic import BaseModel, Field, computed_field
from typing import Dict, List, Optional
from collections import defaultdict

class DataConfig(BaseModel):
    cache_dir: str
    stocks_to_backtest: List[str]
    start_date: str
    end_date: str
    sector_map: Dict[str, str]
    # Optional number of worker processes for backtesting. If None, code will
    # choose min(number of stocks, CPU cores).
    workers: Optional[int] = None

class StrategyParamsConfig(BaseModel):
    bb_length: int = Field(..., gt=0)
    bb_std: float = Field(..., gt=0)
    bb_weekly_length: int = Field(10, gt=0)
    bb_weekly_std: float = Field(2.5, gt=0)
    bb_monthly_length: int = Field(6, gt=0)
    bb_monthly_std: float = Field(3.0, gt=0)
    rsi_length: int = Field(..., gt=0)
    hurst_length: int = Field(..., gt=0)
    exit_days: int = Field(..., gt=0)
    min_history_days: int = Field(..., gt=0)
    liquidity_lookback_days: int = Field(..., gt=0)

class FiltersConfig(BaseModel):
    sector_vol_threshold: float = Field(..., ge=0)
    liquidity_turnover_crores: float = Field(..., ge=0)
    adf_p_value_threshold: float = Field(..., ge=0, le=1)
    hurst_threshold: float = Field(..., ge=0, le=1)

class ScoringConfig(BaseModel):
    liquidity_score_min_turnover_crores: float = Field(..., ge=0)
    liquidity_score_max_turnover_crores: float = Field(..., ge=0)
    regime_score_min_volatility_pct: float = Field(..., ge=0)
    regime_score_max_volatility_pct: float = Field(..., ge=0)
    hurst_score_min_h: float = Field(..., ge=0, le=1)
    hurst_score_max_h: float = Field(..., ge=0, le=1)
    adf_score_min_pvalue: float = Field(..., ge=0, le=1)
    adf_score_max_pvalue: float = Field(..., ge=0, le=1)

class LLMConfig(BaseModel):
    use_llm_audit: bool = False
    provider: str
    confidence_threshold: float = Field(..., ge=0, le=1)
    min_composite_score_for_llm: float = Field(0.05, ge=0, le=1)
    model: str
    prompt_template_path: str

class CostModelConfig(BaseModel):
    brokerage_rate: float = Field(..., ge=0)
    brokerage_max: float = Field(..., ge=0)
    stt_rate: float = Field(..., ge=0)
    assumed_trade_value_inr: float = Field(..., ge=0)
    slippage_volume_threshold: int = Field(..., ge=0)
    slippage_rate_high_liquidity: float = Field(..., ge=0)
    slippage_rate_low_liquidity: float = Field(..., ge=0)


class ExitLogicConfig(BaseModel):
    use_atr_exit: bool
    atr_period: int = Field(..., gt=0)
    atr_stop_loss_multiplier: float = Field(..., gt=0)
    max_holding_days: int = Field(..., gt=0)

class SignalLogicConfig(BaseModel):
    require_daily_oversold: bool
    require_weekly_oversold: bool
    require_monthly_not_oversold: bool
    rsi_threshold: int = Field(..., gt=0, lt=100)

class Signal(BaseModel):
    """
    Represents a potential trade signal.
    """
    entry_price: float
    stop_loss: float
    exit_target_days: int
    frames_aligned: List[str]
    sector_vol: float

class ValidationScores(BaseModel):
    """
    Holds the float score (0.0-1.0) from each validation guardrail.
    """
    liquidity_score: float
    regime_score: float
    stat_score: float

    @computed_field
    @property
    def composite_score(self) -> float:
        """The geometric mean of the individual scores."""
        return self.liquidity_score * self.regime_score * self.stat_score

class Trade(BaseModel):
    """
    Represents a completed trade with its result.
    """
    stock: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    net_return_pct: float
    confidence_score: float
    signal: Signal # Keep track of the signal that generated the trade

    model_config = {"arbitrary_types_allowed": True}


class Opportunity(BaseModel):
    """
    Represents a potential trade opportunity that has been validated.
    """
    stock: str
    signal_date: pd.Timestamp
    signal: Signal
    confidence_score: float

    model_config = {"arbitrary_types_allowed": True}


class BacktestMetrics(BaseModel):
    """
    Holds the statistics for the signal attrition funnel.
    """
    potential_signals: int = 0
    rejections_by_guard: Dict[str, int] = Field(default_factory=lambda: defaultdict(int))
    rejections_by_llm: int = 0
    trades_executed: int = 0


class RunMetadata(BaseModel):
    """
    Holds metadata about a specific backtest run for reproducibility.
    """
    run_timestamp: str
    config_path: str
    git_commit_hash: str


class SensitivityAnalysisConfig(BaseModel):
    """
    Configuration for the sensitivity analysis module.
    """
    parameter_to_vary: str
    start_value: float
    end_value: float
    step_size: float


class BacktestSummary(BaseModel):
    """
    Represents the aggregated results of a backtest run.
    """
    parameter_value: float
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    net_return_pct_mean: float
    net_return_pct_std: float


class Config(BaseModel):
    """
    Top-level configuration model.
    """
    data: DataConfig
    strategy_params: StrategyParamsConfig
    filters: FiltersConfig
    scoring: ScoringConfig
    signal_logic: SignalLogicConfig
    llm: LLMConfig
    cost_model: CostModelConfig
    exit_logic: ExitLogicConfig
    sensitivity_analysis: Optional[SensitivityAnalysisConfig] = None
