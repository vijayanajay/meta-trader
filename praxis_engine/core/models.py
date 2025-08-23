"""
Pydantic models for the application.
"""
from pydantic import BaseModel, Field
from typing import Dict, List

class DataConfig(BaseModel):
    cache_dir: str
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

class Config(BaseModel):
    """
    Top-level configuration model.
    """
    data: DataConfig
    strategy_params: StrategyParamsConfig
    filters: FiltersConfig
    llm: LLMConfig
