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

class FiltersConfig(BaseModel):
    sector_vol_threshold: float = Field(..., ge=0)
    liquidity_turnover_crores: float = Field(..., ge=0)
    adf_p_value_threshold: float = Field(..., ge=0, le=1)
    hurst_threshold: float = Field(..., ge=0, le=1)

class LLMConfig(BaseModel):
    confidence_threshold: float = Field(..., ge=0, le=1)
    model: str
    prompt_template_path: str

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
