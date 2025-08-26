import pandas as pd
import pytest
from praxis_engine.core.models import CostModelConfig, Signal, Trade
from praxis_engine.services.execution_simulator import ExecutionSimulator

@pytest.fixture
def cost_model_config() -> CostModelConfig:
    """Provides a sample cost model configuration."""
    return CostModelConfig(
        brokerage_rate=0.0003,  # 0.03%
        brokerage_min=20.0,
        stt_rate=0.00025,      # 0.025%
        slippage_pct=0.001,    # 0.1%
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

def test_simulate_trade_profit(execution_simulator: ExecutionSimulator, sample_signal: Signal):
    """
    Tests a profitable trade scenario.
    Entry: 100, Exit: 110
    """
    entry_price = 100.0
    exit_price = 110.0

    # --- Manual Calculation ---
    cm = execution_simulator.cost_model

    # Entry
    entry_price_adj = entry_price * (1 + cm.slippage_pct)
    entry_costs = max(cm.brokerage_rate * entry_price_adj, cm.brokerage_min) + (cm.stt_rate * entry_price_adj)
    final_entry_price = entry_price_adj + entry_costs

    # Exit
    exit_price_adj = exit_price * (1 - cm.slippage_pct)
    exit_costs = max(cm.brokerage_rate * exit_price_adj, cm.brokerage_min) + (cm.stt_rate * exit_price_adj)
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
        entry_volume=10000
    )

    assert trade is not None
    assert trade.net_return_pct == pytest.approx(expected_return, abs=1e-9)

def test_simulate_trade_loss(execution_simulator: ExecutionSimulator, sample_signal: Signal):
    """
    Tests a losing trade scenario.
    Entry: 100, Exit: 90
    """
    entry_price = 100.0
    exit_price = 90.0

    # --- Manual Calculation ---
    cm = execution_simulator.cost_model

    # Entry
    entry_price_adj = entry_price * (1 + cm.slippage_pct)
    entry_costs = max(cm.brokerage_rate * entry_price_adj, cm.brokerage_min) + (cm.stt_rate * entry_price_adj)
    final_entry_price = entry_price_adj + entry_costs

    # Exit
    exit_price_adj = exit_price * (1 - cm.slippage_pct)
    exit_costs = max(cm.brokerage_rate * exit_price_adj, cm.brokerage_min) + (cm.stt_rate * exit_price_adj)
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
        entry_volume=10000
    )

    assert trade is not None
    assert trade.net_return_pct == pytest.approx(expected_return, abs=1e-9)
