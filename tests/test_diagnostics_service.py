import pandas as pd
import pytest
from praxis_engine.services.diagnostics_service import DiagnosticsService
from praxis_engine.core.models import DrawdownPeriod

@pytest.fixture
def sample_trades_no_drawdown() -> pd.DataFrame:
    """Creates a sample DataFrame of trades where equity always increases."""
    data = {
        "exit_date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
        "net_return_pct": [0.10, 0.05, 0.02],
        "stock": ["A", "B", "C"],
        "exit_reason": ["PROFIT_TARGET"] * 3,
    }
    return pd.DataFrame(data)

def test_analyze_drawdown_with_clear_drawdown_period(sample_trades_with_drawdown):
    """
    Tests that analyze_drawdown correctly identifies the maximum drawdown period.
    """
    trades_df = sample_trades_with_drawdown
    result = DiagnosticsService.analyze_drawdown(trades_df)

    assert result is not None
    assert isinstance(result, DrawdownPeriod)

    # The equity curve is [1.0, 1.1, 1.21, 1.089, 0.9801, 1.07811]
    # The peak is 1.21, which occurs after the trade on 2023-01-03 (index 1 of df).
    # The trough is 0.9801, which occurs after the trade on 2023-01-05 (index 3 of df).
    assert result.start_date == pd.Timestamp("2023-01-03")
    assert result.end_date == pd.Timestamp("2023-01-05")

    assert result.peak_value == pytest.approx(1.21)
    assert result.trough_value == pytest.approx(0.9801, abs=1e-4)

    expected_drawdown = (0.9801 - 1.21) / 1.21
    assert result.max_drawdown_pct == pytest.approx(expected_drawdown)

    # The trade indices should be from the peak to the trough (inclusive)
    # df indices are 1, 2, 3
    assert result.trade_indices == [1, 2, 3]

def test_analyze_drawdown_with_no_drawdown(sample_trades_no_drawdown):
    """
    Tests that analyze_drawdown returns None when there is no drawdown.
    """
    trades_df = sample_trades_no_drawdown
    result = DiagnosticsService.analyze_drawdown(trades_df)

    assert result is None

def test_analyze_drawdown_with_empty_dataframe():
    """
    Tests that analyze_drawdown returns None for an empty DataFrame.
    """
    empty_df = pd.DataFrame(columns=["exit_date", "net_return_pct"])
    result = DiagnosticsService.analyze_drawdown(empty_df)

    assert result is None

def test_analyze_drawdown_with_single_trade():
    """
    Tests that analyze_drawdown handles a single trade correctly.
    """
    single_trade_df = pd.DataFrame({
        "exit_date": [pd.Timestamp("2023-01-01")],
        "net_return_pct": [0.05]
    })
    result = DiagnosticsService.analyze_drawdown(single_trade_df)
    assert result is None

    single_loss_df = pd.DataFrame({
        "exit_date": [pd.Timestamp("2023-01-01")],
        "net_return_pct": [-0.05]
    })
    result = DiagnosticsService.analyze_drawdown(single_loss_df)
    # A single loss is a drawdown from the starting equity of 1.0
    assert result is not None
    assert result.max_drawdown_pct == pytest.approx(-0.05)
    assert result.trade_indices == [0]
