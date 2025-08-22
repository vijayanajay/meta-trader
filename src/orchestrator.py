#
# orchestrator.py
#
"""
The Orchestrator component that drives the self-improving loop.
"""
from typing import Type
import logging

from services import (
    ConfigService,
    StateManager,
    DataService,
    StrategyEngine,
    Backtester,
    ReportGenerator,
    LLMService,
)
from core.models import RunState, StrategyDefinition, PerformanceReport
from core.strategy import SmaCross

# H-10: No print() statements outside main.py. Use logger.
logger = logging.getLogger(__name__)


class Orchestrator:
    """
    The main orchestrator for the trading strategy optimization loop.

    This class coordinates all the services to execute the main feedback loop:
    1. Load state (or create new).
    2. Run backtest with current strategy.
    3. Generate performance report.
    4. Save state.
    5. Get next strategy suggestion from LLM.
    6. Repeat.

    It is designed to be stateless itself, with all run-specific information
    managed through the services it coordinates, primarily the StateManager.
    """

    # H-2: Services are injected, not instantiated here.
    def __init__(
        self,
        config_service: ConfigService,
        state_manager: StateManager,
        data_service: DataService,
        strategy_engine: StrategyEngine,
        backtester: Backtester,
        report_generator: ReportGenerator,
        llm_service: LLMService,
    ) -> None:
        """
        Initializes the Orchestrator with all required services.
        """
        self.config = config_service.load_config()
        self.state_manager = state_manager
        self.data_service = data_service
        self.strategy_engine = strategy_engine
        self.backtester = backtester
        self.report_generator = report_generator
        self.llm_service = llm_service

        self.baseline_strategy: Type[SmaCross] = SmaCross

    # impure
    def run(self) -> None:
        """
        The main entry point to start the optimization process.

        It iterates through each ticker specified in the config and runs
        the full optimization loop for it.
        """
        logger.info("Orchestrator starting run.")
        for ticker in self.config.app.tickers:
            logger.info(f"Processing ticker: {ticker}")
            try:
                self._run_for_ticker(ticker)
            except Exception:
                logger.exception(
                    f"A critical error occurred during the run for ticker {ticker}. "
                    "Aborting process for this ticker."
                )
        logger.info("Orchestrator run finished.")

    # impure
    def _run_for_ticker(self, ticker: str) -> None:
        """
        Executes the full optimization loop for a single ticker.
        This includes loading state, running the backtest iterations,
        and interacting with the LLM.
        """
        logger.info(f"[{ticker}] Starting optimization loop.")

        # 1. Load state or initialize a new one
        run_state = self.state_manager.load_state(ticker)
        logger.info(f"[{ticker}] Loaded state. Current iteration: {run_state.iteration_number}")

        # 2. Get data
        train_data, _ = self.data_service.get_data(ticker)
        logger.info(f"[{ticker}] Loaded training data: {len(train_data)} rows.")

        # 3. Main optimization loop
        while run_state.iteration_number < self.config.app.iterations:
            iteration = run_state.iteration_number
            logger.info(f"[{ticker}] Running Iteration {iteration}/{self.config.app.iterations}")

            # Get the strategy to test for this iteration
            if iteration == 0:
                # Iteration 0 is always the hard-coded baseline strategy
                strategy_def = self._get_baseline_strategy_def()
            else:
                # Subsequent iterations use the suggestion from the last report
                last_report = run_state.history[-1]
                if not last_report.next_strategy_suggestion:
                    logger.error(f"[{ticker}] No strategy suggestion found from previous iteration. Aborting.")
                    break
                strategy_def = last_report.next_strategy_suggestion

            # Run backtest and generate report
            try:
                strategy_class = self.strategy_engine.process(
                    train_data.copy(), strategy_def, self.config.backtest.trade_size
                )
                stats, trades = self.backtester.run(
                    train_data, strategy_class, self.config.backtest
                )
                report = self.report_generator.generate(stats, trades, strategy_def)

                # Pruning logic
                if report.performance.sharpe_ratio < self.config.app.sharpe_threshold:
                    logger.warning(
                        f"[{ticker}] Iteration {iteration} pruned. "
                        f"Sharpe Ratio ({report.performance.sharpe_ratio:.2f}) is below threshold "
                        f"({self.config.app.sharpe_threshold})."
                    )
                    report.is_pruned = True

            except Exception as e:
                logger.exception(f"[{ticker}] Backtest failed for iteration {iteration}: {e}")
                # Create a pruned report for the failure
                report = self._create_failure_report(strategy_def)

            # Get LLM suggestion for the next iteration
            if (iteration + 1) < self.config.app.iterations:
                best_strategy_to_date = self._find_best_strategy(run_state)
                llm_context_report = report if not report.is_pruned else self._find_best_report(run_state)

                if llm_context_report:
                    suggestion = self.llm_service.get_suggestion(
                        ticker=ticker,
                        history=run_state.history + [report],
                        failed_strategy=report if report.is_pruned else None,
                        best_strategy_so_far=best_strategy_to_date,
                    )
                    report.next_strategy_suggestion = suggestion
                else:
                    # This happens if the very first iteration is pruned.
                    # We need a baseline to provide to the LLM.
                    baseline_report = self._create_baseline_report(train_data)
                    suggestion = self.llm_service.get_suggestion(
                        ticker=ticker,
                        history=[baseline_report],
                        failed_strategy=report,
                        best_strategy_so_far=self._get_baseline_strategy_def(),
                    )
                    report.next_strategy_suggestion = suggestion

            # Update and save state
            run_state.history.append(report)
            run_state.iteration_number += 1
            self.state_manager.save_state(ticker, run_state)
            logger.info(f"[{ticker}] Iteration {iteration} complete. State saved.")

        logger.info(f"[{ticker}] Optimization loop finished.")
        best_report = self._find_best_report(run_state)
        if best_report:
            logger.info(
                f"[{ticker}] Best strategy found: '{best_report.strategy.strategy_name}' "
                f"with Sharpe Ratio: {best_report.performance.sharpe_ratio:.2f}"
            )
        else:
            logger.warning(f"[{ticker}] No successful strategies were found after {run_state.iteration_number} iterations.")

    def _get_baseline_strategy_def(self) -> StrategyDefinition:
        """Returns the hard-coded baseline strategy definition."""
        from core.models import Indicator
        return StrategyDefinition(
            strategy_name="SMA_Crossover_Baseline",
            indicators=[
                Indicator(name="sma_fast", function="sma", params={"length": 50}),
                Indicator(name="sma_slow", function="sma", params={"length": 200}),
            ],
            buy_condition="sma_fast > sma_slow",
            sell_condition="sma_fast < sma_slow",
        )

    def _create_failure_report(self, strategy_def: StrategyDefinition) -> PerformanceReport:
        """Creates a placeholder report for a failed backtest iteration."""
        logger.error(f"Creating failure report for strategy: {strategy_def.strategy_name}")
        # Create a mostly empty report, but mark it as pruned.
        return PerformanceReport.create_pruned(strategy_def)

    def _find_best_strategy(self, run_state: RunState) -> StrategyDefinition:
        """Finds the best-performing, non-pruned strategy from the history."""
        best_report = self._find_best_report(run_state)
        return best_report.strategy if best_report else self._get_baseline_strategy_def()

    def _find_best_report(self, run_state: RunState) -> PerformanceReport | None:
        """Finds the best-performing, non-pruned report from the history."""
        best_report = None
        max_sharpe = -float("inf")
        for report in run_state.history:
            if not report.is_pruned and report.performance.sharpe_ratio > max_sharpe:
                max_sharpe = report.performance.sharpe_ratio
                best_report = report
        return best_report

    def _create_baseline_report(self, data: "pd.DataFrame") -> PerformanceReport:
        """Runs a backtest for the baseline strategy to get a report."""
        import pandas as pd
        strategy_def = self._get_baseline_strategy_def()
        strategy_class = self.strategy_engine.process(
            data.copy(), strategy_def, self.config.backtest.trade_size
        )
        stats, trades = self.backtester.run(data, strategy_class, self.config.backtest)
        return self.report_generator.generate(stats, trades, strategy_def)
