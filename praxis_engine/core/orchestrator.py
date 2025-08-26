"""
The main orchestrator for running backtests.
"""
from typing import List
import pandas as pd

from praxis_engine.core.models import Config, Trade
from praxis_engine.services.data_service import DataService
from praxis_engine.services.signal_engine import SignalEngine
from praxis_engine.services.validation_service import ValidationService
from praxis_engine.services.llm_audit_service import LLMAuditService
from praxis_engine.services.execution_simulator import ExecutionSimulator
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)

class Orchestrator:
    """
    Orchestrates the services to run a backtest.
    """

    def __init__(self, config: Config):
        self.config = config
        self.data_service = DataService(config.data.cache_dir)
        self.signal_engine = SignalEngine(config.strategy_params, config.signal_logic)
        self.validation_service = ValidationService(config.filters, config.strategy_params)
        self.execution_simulator = ExecutionSimulator(config.cost_model)
        self.llm_audit_service = LLMAuditService(
            config.llm,
            self.signal_engine,
            self.validation_service,
            self.execution_simulator,
        )

    def run_backtest(self, stock: str, start_date: str, end_date: str) -> List[Trade]:
        """
        Runs a walk-forward backtest for a single stock.
        """
        log.info(f"Starting backtest for {stock} from {start_date} to {end_date}...")

        sector_ticker = self.config.data.sector_map.get(stock)
        full_df = self.data_service.get_data(stock, start_date, end_date, sector_ticker)

        if full_df is None or full_df.empty:
            log.warning(f"No data found for {stock}. Skipping backtest.")
            return []

        trades: List[Trade] = []
        min_history_days = self.config.strategy_params.min_history_days

        for i in range(min_history_days, len(full_df) - 1): # -1 to ensure there's a next day for entry
            window = full_df.iloc[0:i]
            signal_date = window.index[-1]

            # The signal generation should be based on the data available at that point in time
            signal = self.signal_engine.generate_signal(window.copy())
            if not signal:
                continue

            log.info(f"Preliminary signal found for {stock} on {signal_date.date()}")

            validation = self.validation_service.validate(window, signal)
            if not validation.is_valid:
                log.info(f"Signal for {stock} rejected by guardrails: {validation.reason}")
                continue

            confidence_score = self.llm_audit_service.get_confidence_score(
                window, signal, validation
            )

            if confidence_score < self.config.llm.confidence_threshold:
                log.info(f"Signal for {stock} rejected by LLM audit (score: {confidence_score})")
                continue

            # --- DATA LEAKAGE FIX: Determine trade parameters inside the loop ---
            # The orchestrator is allowed to "see the future" relative to the window,
            # because it simulates the passage of time. The simulator is not.

            entry_date_actual = full_df.index[i]
            entry_price = full_df.iloc[i]["Open"]
            entry_volume = full_df.iloc[i]["Volume"]

            exit_date_target_index = i + signal.exit_target_days
            if exit_date_target_index >= len(full_df):
                # If exit is beyond the dataset, exit on the last day
                exit_date_actual = full_df.index[-1]
                exit_price = full_df.iloc[-1]["Close"]
            else:
                exit_date_actual = full_df.index[exit_date_target_index]
                exit_price = full_df.iloc[exit_date_target_index]["Close"]

            trade = self.execution_simulator.simulate_trade(
                stock=stock,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_date=entry_date_actual,
                exit_date=exit_date_actual,
                signal=signal,
                confidence_score=confidence_score,
                entry_volume=entry_volume
            )

            if trade:
                log.info(f"Trade simulated: {trade}")
                trades.append(trade)

        log.info(f"Backtest for {stock} complete. Found {len(trades)} trades.")
        return trades
