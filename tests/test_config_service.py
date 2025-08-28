import pytest
from pydantic import ValidationError
from pathlib import Path

from praxis_engine.services.config_service import ConfigService
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
brokerage_max = 20.0
stt_rate = 0.00025
assumed_trade_value_inr = 100000
slippage_volume_threshold = 1000000
slippage_rate_high_liquidity = 0.001
slippage_rate_low_liquidity = 0.005

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
provider = "test"
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = true
require_monthly_not_oversold = true
rsi_threshold = 30

[exit_logic]
use_atr_exit = false
atr_period = 10
atr_stop_loss_multiplier = 2.0
max_holding_days = 25
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    config = ConfigService(str(config_file)).load_config()

    assert isinstance(config, Config)
    assert config.data.cache_dir == "test_cache"
    assert config.strategy_params.bb_length == 10
    assert config.filters.sector_vol_threshold == 25.0
    assert config.llm.model == "test/model"
    assert config.exit_logic.use_atr_exit is False

def test_load_config_missing_key(tmp_path: Path) -> None:
    """
    Tests that a ValidationError is raised if a required key is missing.
    """
    config_content = """
[data]
cache_dir = "test_cache"
# stocks_to_backtest is missing
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
brokerage_max = 20.0
stt_rate = 0.00025
assumed_trade_value_inr = 100000
slippage_volume_threshold = 1000000
slippage_rate_high_liquidity = 0.001
slippage_rate_low_liquidity = 0.005

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
provider = "test"
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = true
require_monthly_not_oversold = true
rsi_threshold = 30

[exit_logic]
use_atr_exit = false
atr_period = 10
atr_stop_loss_multiplier = 2.0
max_holding_days = 25
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    with pytest.raises(ValidationError):
        ConfigService(str(config_file)).load_config()


def test_load_config_with_sensitivity_analysis(tmp_path: Path) -> None:
    """
    Tests that a config file with the optional sensitivity_analysis section is loaded correctly.
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
brokerage_max = 20.0
stt_rate = 0.00025
assumed_trade_value_inr = 100000
slippage_volume_threshold = 1000000
slippage_rate_high_liquidity = 0.001
slippage_rate_low_liquidity = 0.005

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
provider = "test"
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = true
require_monthly_not_oversold = true
rsi_threshold = 30

[exit_logic]
use_atr_exit = false
atr_period = 10
atr_stop_loss_multiplier = 2.0
max_holding_days = 25

[sensitivity_analysis]
parameter_to_vary = "filters.sector_vol_threshold"
start_value = 20.0
end_value = 30.0
step_size = 1.0
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    config = ConfigService(str(config_file)).load_config()

    assert config.sensitivity_analysis is not None
    assert config.sensitivity_analysis.parameter_to_vary == "filters.sector_vol_threshold"
    assert config.sensitivity_analysis.start_value == 20.0
    assert config.sensitivity_analysis.end_value == 30.0
    assert config.sensitivity_analysis.step_size == 1.0

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
brokerage_max = 20.0
stt_rate = 0.00025
assumed_trade_value_inr = 100000
slippage_volume_threshold = 1000000
slippage_rate_high_liquidity = 0.001
slippage_rate_low_liquidity = 0.005

[filters]
sector_vol_threshold = 25.0
liquidity_turnover_crores = 2.0
adf_p_value_threshold = 0.1
hurst_threshold = 0.5

[llm]
provider = "test"
confidence_threshold = 0.6
model = "test/model"
prompt_template_path = "test/prompt.txt"

[signal_logic]
require_daily_oversold = true
require_weekly_oversold = true
require_monthly_not_oversold = true
rsi_threshold = 30

[exit_logic]
use_atr_exit = false
atr_period = 10
atr_stop_loss_multiplier = 2.0
max_holding_days = 25
"""
    config_file = tmp_path / "config.ini"
    config_file.write_text(config_content)

    with pytest.raises(ValidationError):
        ConfigService(str(config_file)).load_config()
