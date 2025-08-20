import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from self_improving_quant.core.orchestrator import Orchestrator, _calculate_edge_score

# Test data for edge score calculation
@pytest.mark.parametrize(
    "stats, expected",
    [
        (pd.Series({"Return [%]": 10, "Exposure Time [%]": 50, "Sharpe Ratio": 1.5, "Sortino Ratio": 2.0}), 0.15),
        (pd.Series({"Return [%]": -5, "Exposure Time [%]": 50, "Sharpe Ratio": -0.5, "Sortino Ratio": 0.8}), -0.0625),
        (pd.Series({"Return [%]": 10, "Exposure Time [%]": 0, "Sharpe Ratio": 1.5, "Sortino Ratio": 2.0}), None),
        (pd.Series({"Return [%]": 10, "Exposure Time [%]": 50, "Sharpe Ratio": 1.5, "Sortino Ratio": 0}), None),
        (pd.Series({}), None),
    ],
)
def test_calculate_edge_score(stats: pd.Series, expected: float | None) -> None:
    """Tests the edge score calculation logic."""
    result = _calculate_edge_score(stats)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)

# Mocked integration test for the orchestrator
@patch("self_improving_quant.core.orchestrator.load_state", return_value=[])
@patch("self_improving_quant.core.orchestrator.fetch_and_split_data")
@patch("self_improving_quant.core.orchestrator.LLMService")
def test_orchestrator_run_loop(
    mock_llm_service: MagicMock, mock_fetch_data: MagicMock, mock_load_state: MagicMock
) -> None:
    """Tests the main run loop of the orchestrator with mocked services."""
    # Arrange
    mock_fetch_data.return_value = (MagicMock(), MagicMock())  # train_data, validation_data

    mock_llm_instance = mock_llm_service.return_value
    mock_llm_instance.get_strategy_suggestion.return_value = """
    {
      "rationale": "A mock strategy.",
      "indicators": [{"name": "SMA", "type": "sma", "params": {"length": 10}}],
      "buy_signal": "self.data.SMA[-1] > self.data.Close[-1]",
      "sell_signal": "self.data.SMA[-1] < self.data.Close[-1]"
    }
    """

    orchestrator = Orchestrator(ticker="MOCK.NS", num_iterations=2)

    # Act
    with patch("self_improving_quant.core.orchestrator._run_backtest") as mock_run_backtest:
        mock_run_backtest.return_value = pd.Series({
            "Return [%]": 10, "Exposure Time [%]": 50, "Sharpe Ratio": 1.5, "Sortino Ratio": 2.0,
            "Start": "2022-01-01", "End": "2023-01-01", "Duration": "365 days",
            "Equity Final [$]": 110000, "Equity Peak [$]": 115000,
            "Buy & Hold Return [%]": 5.0, "Return (Ann.) [%]": 10.0,
            "Volatility (Ann.) [%]": 15.0, "Calmar Ratio": 0.5,
            "Max. Drawdown [%]": -10.0, "Avg. Drawdown [%]": -5.0,
            "Max. Drawdown Duration": 30, "Avg. Drawdown Duration": 15,
            "# Trades": 20, "Win Rate [%]": 60.0, "Best Trade [%]": 5.0,
            "Worst Trade [%]": -3.0, "Avg. Trade [%]": 1.0,
            "Max. Trade Duration": 10, "Avg. Trade Duration": 5,
            "Profit Factor": 1.5, "Expectancy [%]": 1.0, "SQN": 1.5,
        })
        orchestrator.run()

    # Assert
    assert len(orchestrator.history) == 2
    assert mock_llm_instance.get_strategy_suggestion.call_count == 2
    assert orchestrator.history[0].edge_score is not None
    assert orchestrator.history[1].edge_score is not None
