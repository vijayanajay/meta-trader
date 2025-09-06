import pandas as pd
import pytest
from praxis_engine.services.diagnostics_service import DiagnosticsService
from praxis_engine.core.models import DrawdownPeriod


def test_analyze_drawdown_with_sample_data():
    """
    Tests the analyze_drawdown method with a handcrafted DataFrame
    containing a clear drawdown period.
    """
    data = {
        "exit_date": pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
                "2023-01-06",
            ]
        ),
        "net_return_pct": [0.1, 0.05, -0.15, -0.1, 0.05, 0.2],
    }
    trades_df = pd.DataFrame(data)

    # Expected values
    # Equity curve:
    # 1.1
    # 1.1 * 1.05 = 1.155 (Peak)
    # 1.155 * 0.85 = 0.98175
    # 0.98175 * 0.9 = 0.883575 (Trough)
    # 0.883575 * 1.05 = 0.92775375
    # 0.92775375 * 1.2 = 1.1133045
    #
    # Drawdown = (trough - peak) / peak
    # (0.883575 - 1.155) / 1.155 = -0.235
    expected_peak_date = pd.Timestamp("2023-01-02")
    expected_trough_date = pd.Timestamp("2023-01-04")
    expected_max_drawdown = (0.883575 - 1.155) / 1.155

    result = DiagnosticsService.analyze_drawdown(trades_df)

    assert result is not None
    assert isinstance(result, DrawdownPeriod)
    assert result.start_date == expected_peak_date
    assert result.end_date == expected_trough_date
    assert result.peak_value == pytest.approx(1.155)
    assert result.trough_value == pytest.approx(0.883575)
    assert result.max_drawdown_pct == pytest.approx(expected_max_drawdown)
    assert result.trade_indices == [1, 2, 3]


def test_analyze_drawdown_with_empty_dataframe():
    """
    Tests that analyze_drawdown returns None for an empty DataFrame.
    """
    trades_df = pd.DataFrame(columns=["exit_date", "net_return_pct"])
    result = DiagnosticsService.analyze_drawdown(trades_df)
    assert result is None


def test_analyze_drawdown_with_no_losses():
    """
    Tests that analyze_drawdown correctly identifies the 'drawdown'
    of a single small drop in an otherwise profitable stream.
    """
    data = {
        "exit_date": pd.to_datetime(
            ["2023-01-01", "2023-01-02", "2023-01-03"]
        ),
        "net_return_pct": [0.1, 0.05, -0.02],
    }
    trades_df = pd.DataFrame(data)

    # Equity curve: 1.1, 1.155, 1.1319
    # Drawdown: (1.1319 - 1.155) / 1.155 = -0.02
    result = DiagnosticsService.analyze_drawdown(trades_df)

    assert result is not None
    assert result.start_date == pd.Timestamp("2023-01-02")
    assert result.end_date == pd.Timestamp("2023-01-03")
    assert result.max_drawdown_pct == pytest.approx(-0.02, abs=1e-4)
