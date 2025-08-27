"""
Pydantic models for the application.
"""
import pandas as pd
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class DataConfig(BaseModel):
    cache_dir: str
    stocks_to_backtest: List[str]
    start_date: str
    end_date: str
    sector_map: Dict[str, str]

class StrategyParamsConfig(BaseModel):
    bb_length: int = Field(..., gt=0)
    bb_std: float = Field(..., gt=0)
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

class LLMConfig(BaseModel):
    provider: str
    confidence_threshold: float = Field(..., ge=0, le=1)
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

class ValidationResult(BaseModel):
    """
    Holds the boolean result of each validation guardrail.
    """
    is_valid: bool = True
    liquidity_check: bool = True
    regime_check: bool = True
    stat_check: bool = True
    reason: Optional[str] = None

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

class Config(BaseModel):
    """
    Top-level configuration model.
    """
    data: DataConfig
    strategy_params: StrategyParamsConfig
    filters: FiltersConfig
    signal_logic: SignalLogicConfig
    llm: LLMConfig
    cost_model: CostModelConfig
    exit_logic: ExitLogicConfig
