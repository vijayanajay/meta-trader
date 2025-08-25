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
        self.llm_audit_service = LLMAuditService(config.llm)
        self.execution_simulator = ExecutionSimulator()

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
        min_history_days = 200 # A reasonable minimum number of days for indicators to be stable

        for i in range(min_history_days, len(full_df)):
            window = full_df.iloc[0:i]

            signal = self.signal_engine.generate_signal(window)
            if not signal:
                continue

            log.info(f"Preliminary signal found for {stock} on {window.index[-1].date()}")

            validation = self.validation_service.validate(window, signal)
            if not validation.is_valid:
                log.info(f"Signal for {stock} rejected by guardrails: {validation.reason}")
                continue

            # For now, we'll use a dummy confidence score to avoid LLM calls during dev
            confidence_score = 0.8
            # confidence_score = self.llm_audit_service.get_confidence_score(...)

            if confidence_score < self.config.llm.confidence_threshold:
                log.info(f"Signal for {stock} rejected by LLM audit (score: {confidence_score})")
                continue

            trade = self.execution_simulator.simulate_trade(
                stock=stock,
                df=full_df, # Pass the full df to look into the future for exit price
                signal=signal,
                entry_index=i,
                confidence_score=confidence_score
            )

            if trade:
                log.info(f"Trade simulated: {trade}")
                trades.append(trade)

        log.info(f"Backtest for {stock} complete. Found {len(trades)} trades.")
        return trades
