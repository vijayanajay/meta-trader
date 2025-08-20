from __future__ import annotations

import json
import logging

import pandas as pd
from backtesting import Backtest
from pydantic import ValidationError

from self_improving_quant.core.models import IterationReport, StrategyDefinition
from self_improving_quant.core.strategy import create_strategy_class
from self_improving_quant.services.data_service import fetch_and_split_data
from self_improving_quant.services.llm_service import LLMService
from self_improving_quant.services.state_manager import load_state, save_state

__all__ = ["Orchestrator"]

logger = logging.getLogger(__name__)


def _calculate_edge_score(stats: pd.Series) -> float | None:
    """Calculates the Edge Score from backtest statistics."""
    required = ["Return [%]", "Exposure Time [%]", "Sharpe Ratio", "Sortino Ratio"]
    if not all(k in stats for k in required) or abs(stats["Sortino Ratio"]) < 1e-6 or abs(stats["Exposure Time [%]"]) < 1e-6:
        return None
    # Use absolute values for the ratio part to measure quality of risk-adjusted return
    score = (stats["Return [%]"] / stats["Exposure Time [%]"]) * (abs(stats["Sharpe Ratio"]) / abs(stats["Sortino Ratio"]))
    return float(score)


def _run_backtest(strategy_class: type[Backtest], data: pd.DataFrame) -> pd.Series:
    """Runs a backtest for a given strategy and data."""
    bt = Backtest(data, strategy_class, cash=100_000, commission=0.002)
    stats = bt.run()
    return stats


class Orchestrator:
    """Orchestrates the self-improving quant loop."""

    def __init__(self, ticker: str, num_iterations: int):
        self.ticker = ticker
        self.num_iterations = num_iterations
        self.llm_service = LLMService()
        # H-27: Load state on initialization
        self.history: list[IterationReport] = load_state()

    def _get_initial_strategy(self) -> StrategyDefinition:
        """Returns the hard-coded baseline strategy."""
        return StrategyDefinition(
            rationale="Baseline RSI Crossover strategy.",
            indicators=[{"name": "RSI", "type": "rsi", "params": {"length": 14}}],
            buy_signal="self.data.RSI[-1] < 30",
            sell_signal="self.data.RSI[-1] > 70",
        )

    # impure
    def run(self) -> None:
        """Runs the main improvement loop."""
        train_data, validation_data = fetch_and_split_data(self.ticker)

        start_iteration = len(self.history)
        if start_iteration > 0:
            logger.info(f"Resuming run from iteration {start_iteration}.")
            current_strategy = self.history[-1].strategy
        else:
            current_strategy = self._get_initial_strategy()

        for i in range(start_iteration, self.num_iterations):
            logger.info(f"--- Iteration {i} ---")
            strategy_class = create_strategy_class(current_strategy)
            stats = _run_backtest(strategy_class, train_data)

            edge_score = _calculate_edge_score(stats)
            report = IterationReport(iteration=i, strategy=current_strategy, **stats, edge_score=edge_score)
            self.history.append(report)
            logger.info(f"Strategy Edge Score: {edge_score:.4f}")

            # H-27: Save state after each completed iteration
            save_state(self.history)

            llm_response_str = self.llm_service.get_strategy_suggestion(self.history)
            try:
                current_strategy = StrategyDefinition.model_validate(json.loads(llm_response_str))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse LLM response: {e}")
                break  # End run on bad parse

        self._run_final_validation(validation_data)

    # impure
    def _run_final_validation(self, validation_data: pd.DataFrame) -> None:
        """Runs backtests on the top 3 strategies using the validation dataset."""
        logger.info("\n--- Final Validation ---")
        successful_reports = [r for r in self.history if r.edge_score is not None]
        top_3 = sorted(
            successful_reports,
            key=lambda r: r.edge_score if r.edge_score is not None else -float("inf"),
            reverse=True,
        )[:3]

        if not top_3:
            logger.warning("No successful strategies to validate.")
            return

        for rank, report in enumerate(top_3):
            logger.info(f"Validating Strategy #{rank + 1} (Iteration {report.iteration})")
            strategy_class = create_strategy_class(report.strategy)
            stats = _run_backtest(strategy_class, validation_data)
            edge_score = _calculate_edge_score(stats)
            logger.info(f"  Validation Edge Score: {edge_score:.4f}")
            logger.info(f"  Validation Return [%]: {stats['Return [%]']:.2f}")

        logger.info("\n--- Best Performing Strategy on Validation Data ---")
        # For simplicity, we just log the results. A real system might return the best one.
        # This part could be enhanced to select and show the absolute best.
