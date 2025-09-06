import pandas as pd
import pytest

@pytest.fixture
def sample_trades_with_drawdown() -> pd.DataFrame:
    """
    Creates a sample DataFrame of trades with a clear drawdown period.
    Equity curve: 1.0 -> 1.1 -> 1.21 (peak) -> 1.089 -> 0.9801 (trough) -> 1.07811
    """
    trades_data = [
        {
            "stock": "A",
            "entry_date": pd.Timestamp("2023-01-01"),
            "exit_date": pd.Timestamp("2023-01-02"),
            "holding_period_days": 1,
            "net_return_pct": 0.10,
            "exit_reason": "PROFIT_TARGET",
            "composite_score": 0.8,
            "entry_sector_vol": 18.0,
        },
        {
            "stock": "B",
            "entry_date": pd.Timestamp("2023-01-02"),
            "exit_date": pd.Timestamp("2023-01-03"),
            "holding_period_days": 1,
            "net_return_pct": 0.10,
            "exit_reason": "PROFIT_TARGET",
            "composite_score": 0.8,
            "entry_sector_vol": 18.0,
        },
        {
            "stock": "C",
            "entry_date": pd.Timestamp("2023-01-03"),
            "exit_date": pd.Timestamp("2023-01-04"),
            "holding_period_days": 1,
            "net_return_pct": -0.10,
            "exit_reason": "ATR_STOP_LOSS",
            "composite_score": 0.4,
            "entry_sector_vol": 25.0,
        },
        {
            "stock": "D",
            "entry_date": pd.Timestamp("2023-01-04"),
            "exit_date": pd.Timestamp("2023-01-05"),
            "holding_period_days": 1,
            "net_return_pct": -0.10,
            "exit_reason": "ATR_STOP_LOSS",
            "composite_score": 0.4,
            "entry_sector_vol": 25.0,
        },
        {
            "stock": "E",
            "entry_date": pd.Timestamp("2023-01-05"),
            "exit_date": pd.Timestamp("2023-01-06"),
            "holding_period_days": 1,
            "net_return_pct": 0.10,
            "exit_reason": "PROFIT_TARGET",
            "composite_score": 0.8,
            "entry_sector_vol": 18.0,
        },
    ]
    return pd.DataFrame(trades_data)
