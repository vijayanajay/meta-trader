import pandas as pd
import pytest
import math
from unittest.mock import patch
from praxis_engine.core.models import CostModelConfig, Signal, Trade
from praxis_engine.services.execution_simulator import ExecutionSimulator

@pytest.fixture
def cost_model_config() -> CostModelConfig:
    """Provides a sample cost model configuration."""
    return CostModelConfig(
        brokerage_rate=0.0003,
        brokerage_max=20.0,
        stt_rate=0.00025,
        assumed_trade_value_inr=100000,
        slippage_volume_threshold=1000000,
        slippage_rate_high_liquidity=0.001,
        slippage_rate_low_liquidity=0.005,
    )

@pytest.fixture
def execution_simulator(cost_model_config: CostModelConfig) -> ExecutionSimulator:
    """Provides an instance of the ExecutionSimulator."""
    return ExecutionSimulator(cost_model=cost_model_config)

@pytest.fixture
def sample_signal() -> Signal:
    """Provides a sample signal."""
    return Signal(
        entry_price=100.0,
        stop_loss=95.0,
        exit_target_days=10,
        frames_aligned=["daily"],
        sector_vol=0.15
    )

def test_simulate_trade_profit(execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
    """
    Tests a profitable trade scenario with the new cost model.
    Entry: 100, Exit: 110. This is a low liquidity scenario.
    """
    entry_price = 100.0
    exit_price = 110.0
    daily_volume = 500000  # Below the 1M threshold

    # --- Manual Calculation ---
    cm = execution_simulator.cost_model
    slippage_rate = cm.slippage_rate_low_liquidity

    # Slippage
    entry_slippage = entry_price * slippage_rate
    exit_slippage = exit_price * slippage_rate

    # Entry
    entry_price_adj = entry_price + entry_slippage
    entry_costs = execution_simulator._calculate_costs(entry_price_adj)
    final_entry_price = entry_price_adj + entry_costs

    # Exit
    exit_price_adj = exit_price - exit_slippage
    exit_costs = execution_simulator._calculate_costs(exit_price_adj)
    final_exit_price = exit_price_adj - exit_costs

    expected_return = (final_exit_price / final_entry_price) - 1.0

    trade = execution_simulator.simulate_trade(
        stock="TEST.NS",
        entry_price=entry_price,
        exit_price=exit_price,
        entry_date=pd.Timestamp("2023-01-01"),
        exit_date=pd.Timestamp("2023-01-11"),
        signal=sample_signal,
        confidence_score=0.9,
        entry_volume=daily_volume,
    )

    assert trade is not None
    assert trade.net_return_pct == pytest.approx(expected_return, abs=1e-9)

def test_simulate_trade_loss(execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
    """
    Tests a losing trade scenario with the new cost model.
    Entry: 100, Exit: 90. This is a high liquidity scenario.
    """
    entry_price = 100.0
    exit_price = 90.0
    daily_volume = 2000000  # Above the 1M threshold

    # --- Manual Calculation ---
    cm = execution_simulator.cost_model
    slippage_rate = cm.slippage_rate_high_liquidity

    # Slippage
    entry_slippage = entry_price * slippage_rate
    exit_slippage = exit_price * slippage_rate

    # Entry
    entry_price_adj = entry_price + entry_slippage
    entry_costs = execution_simulator._calculate_costs(entry_price_adj)
    final_entry_price = entry_price_adj + entry_costs

    # Exit
    exit_price_adj = exit_price - exit_slippage
    exit_costs = execution_simulator._calculate_costs(exit_price_adj)
    final_exit_price = exit_price_adj - exit_costs

    expected_return = (final_exit_price / final_entry_price) - 1.0

    trade = execution_simulator.simulate_trade(
        stock="TEST.NS",
        entry_price=entry_price,
        exit_price=exit_price,
        entry_date=pd.Timestamp("2023-01-01"),
        exit_date=pd.Timestamp("2023-01-11"),
        signal=sample_signal,
        confidence_score=0.9,
        entry_volume=daily_volume,
    )

    assert trade is not None
    assert trade.net_return_pct == pytest.approx(expected_return, abs=1e-9)

def test_high_slippage_scenario(execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
    """
    Tests that slippage is high when the trade size is a large fraction of daily volume.
    """
    entry_price = 100.0
    exit_price = 101.0 # Small profit before costs
    daily_volume = 2000 # Low daily volume, trade volume is 1000 (50% of daily volume)

    trade = execution_simulator.simulate_trade(
        stock="TEST.NS",
        entry_price=entry_price,
        exit_price=exit_price,
        entry_date=pd.Timestamp("2023-01-01"),
        exit_date=pd.Timestamp("2023-01-11"),
        signal=sample_signal,
        confidence_score=0.9,
        entry_volume=daily_volume
    )

    assert trade is not None
    # The trade should be unprofitable due to high slippage and costs
    assert trade.net_return_pct < 0

def test_zero_volume_scenario(execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
    """
    Tests that a trade results in a total loss if daily volume is zero.
    """
    trade = execution_simulator.simulate_trade(
        stock="TEST.NS",
        entry_price=100.0,
        exit_price=110.0,
        entry_date=pd.Timestamp("2023-01-01"),
        exit_date=pd.Timestamp("2023-01-11"),
        signal=sample_signal,
        confidence_score=0.9,
        entry_volume=0 # Zero volume
    )

    assert trade is not None
    # Slippage cost should be equal to price, resulting in ~100% loss
    assert trade.net_return_pct == pytest.approx(-1.0, abs=1e-2)

def test_trade_volume_exceeds_daily_volume(execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
    """
    Tests that trade volume is capped at daily_volume in slippage calculation.
    """
    entry_price = 100.0
    exit_price = 110.0
    daily_volume = 500

    with patch.object(execution_simulator, '_calculate_slippage', wraps=execution_simulator._calculate_slippage) as spy_slippage:
        execution_simulator.simulate_trade(
            stock="TEST.NS",
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=pd.Timestamp("2023-01-01"),
            exit_date=pd.Timestamp("2023-01-11"),
            signal=sample_signal,
            confidence_score=0.9,
            entry_volume=daily_volume
        )
        assert spy_slippage.call_count == 2
        # Check that the function was called with the correct arguments
        spy_slippage.assert_any_call(entry_price, daily_volume)
        spy_slippage.assert_any_call(exit_price, daily_volume)


class TestCalculateNetReturn:
    def test_calculate_net_return_logic(self, execution_simulator: ExecutionSimulator) -> None:
        """
        Tests the public helper method `calculate_net_return` directly.
        """
        entry_price = 100.0
        exit_price = 110.0
        daily_volume = 100000

        # This should match the manual calculation in `test_simulate_trade_profit`
        trade = execution_simulator.simulate_trade(
            stock="TEST.NS",
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=pd.Timestamp("2023-01-01"),
            exit_date=pd.Timestamp("2023-01-11"),
            signal=Signal(entry_price=100, stop_loss=95, exit_target_days=10, frames_aligned=["d"], sector_vol=0.15),
            confidence_score=0.9,
            entry_volume=daily_volume
        )
        assert trade is not None
        expected_return = trade.net_return_pct

        calculated_return = execution_simulator.calculate_net_return(
            entry_price=entry_price,
            exit_price=exit_price,
            daily_volume=daily_volume
        )
        assert calculated_return == pytest.approx(expected_return)

    def test_zero_entry_price(self, execution_simulator: ExecutionSimulator, sample_signal: Signal) -> None:
        """
        Tests that a trade with zero entry price returns None.
        """
        trade = execution_simulator.simulate_trade(
            stock="TEST.NS",
            entry_price=0.0,
            exit_price=10.0,
            entry_date=pd.Timestamp("2023-01-01"),
            exit_date=pd.Timestamp("2023-01-11"),
            signal=sample_signal,
            confidence_score=0.9,
            entry_volume=10000
        )
        assert trade is None
