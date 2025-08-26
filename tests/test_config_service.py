"""
Unit tests for the ConfigService.
"""
import pytest
from pydantic import ValidationError
from pathlib import Path

from praxis_engine.services.config_service import load_config
from praxis_engine.core.models import Config

def test_load_config_success(tmp_path: Path) -> None:
    """
    Tests that a valid configuration file is loaded correctly.
    """
    config_content = """
[data]
cache_dir = "test_cache"
stocks_to_backtest = ["TEST.NS"]
start_date = "2022-01-01"
end_date = "2023-01-01"
sector_map = {"TEST": "^TESTINDEX"}

[strategy_params]
bb_length = 10
bb_std = 1.5
rsi_length = 7
hurst_length = 50
exit_days = 10
min_history_days = 200
liquidity_lookback_days = 5

[cost_model]
brokerage_rate = 0.0003
brokerage_min = 20.0
stt_rate = 0.00025
slippage_pct = 0.001

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = true
require_monthly_not_oversold = true
rsi_threshold = 30
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert isinstance(config, Config)
    assert config.data.cache_dir == "test_cache"
    assert config.strategy_params.bb_length == 10
    assert config.filters.sector_vol_threshold == 25.0
    assert config.llm.model == "test/model"

def test_load_config_missing_key(tmp_path: Path) -> None:
    """
    Tests that a ValidationError is raised if a required key is missing.
    """
    config_content = """
[data]
cache_dir = "test_cache"
# sector_map is missing

[strategy_params]
bb_length = 10
bb_std = 1.5
rsi_length = 7
hurst_length = 50
exit_days = 10
min_history_days = 200
liquidity_lookback_days = 5

[cost_model]
brokerage_rate = 0.0003
brokerage_min = 20.0
stt_rate = 0.00025
slippage_pct = 0.001

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    with pytest.raises(ValidationError):
        load_config(str(config_file))

def test_load_config_invalid_type(tmp_path: Path) -> None:
    """
    Tests that a ValidationError is raised if a value has an incorrect type.
    """
    config_content = """
[data]
cache_dir = "test_cache"
stocks_to_backtest = ["TEST.NS"]
start_date = "2022-01-01"
end_date = "2023-01-01"
sector_map = {"TEST": "^TESTINDEX"}

[strategy_params]
bb_length = "not-an-int"  # Invalid type
bb_std = 1.5
rsi_length = 7
hurst_length = 50
exit_days = 10
min_history_days = 200
liquidity_lookback_days = 5

[cost_model]
brokerage_rate = 0.0003
brokerage_min = 20.0
stt_rate = 0.00025
slippage_pct = 0.001

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    with pytest.raises(ValidationError):
        load_config(str(config_file))
