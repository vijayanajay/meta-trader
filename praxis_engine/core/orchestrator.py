"""
The main orchestrator for running backtests.
"""
from typing import List, Dict
import pandas as pd

import datetime
from typing import Optional

from praxis_engine.core.indicators import atr
from praxis_engine.core.models import Config, Trade, Opportunity
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
        self.llm_audit_service = LLMAuditService(config.llm)

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
        historical_returns: List[float] = []
        min_history_days = self.config.strategy_params.min_history_days
        atr_col_name = f"ATR_{self.config.exit_logic.atr_period}"

        for i in range(min_history_days, len(full_df) - 1):  # -1 to ensure there's a next day for entry
            window = full_df.iloc[0:i].copy() # Use a copy to avoid SettingWithCopyWarning
            signal_date = window.index[-1]

            # --- FIX: Point-in-time correct ATR calculation ---
            if self.config.exit_logic.use_atr_exit:
                atr_series = atr(
                    window["High"],
                    window["Low"],
                    window["Close"],
                    length=self.config.exit_logic.atr_period,
                )
                if atr_series is not None:
                    window[atr_col_name] = atr_series
                    # FIX: inplace=True on a copy can fail silently. Reassign instead.
                    window[atr_col_name] = window[atr_col_name].bfill()


            signal = self.signal_engine.generate_signal(window)
            if not signal:
                continue

            log.debug(f"Preliminary signal found for {stock} on {signal_date.date()}")

            validation = self.validation_service.validate(window, signal)
            if not validation.is_valid:
                log.debug(f"Signal for {stock} rejected by guardrails: {validation.reason}")
                continue

            log.info(f"Validated signal found for {stock} on {signal_date.date()}")

            historical_stats = self._calculate_stats_from_returns(historical_returns)

            confidence_score = self.llm_audit_service.get_confidence_score(
                historical_stats=historical_stats,
                signal=signal,
                df_window=window,
            )

            if confidence_score < self.config.llm.confidence_threshold:
                log.info(f"Signal for {stock} rejected by LLM audit (score: {confidence_score})")
                continue

            entry_date_actual = full_df.index[i]
            entry_price = full_df.iloc[i]["Open"]
            entry_volume = full_df.iloc[i]["Volume"]

            exit_date_actual, exit_price = self._determine_exit(i, entry_price, full_df, window)

            assert exit_date_actual is not None and exit_price is not None

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
                historical_returns.append(trade.net_return_pct)

        log.info(f"Backtest for {stock} complete. Found {len(trades)} trades.")
        return trades

    def _determine_exit(self, entry_index: int, entry_price: float, full_df: pd.DataFrame, window_df: pd.DataFrame):
        """ Determines the exit date and price for a trade. """
        atr_col_name = f"ATR_{self.config.exit_logic.atr_period}"
        # FIX: Check for NaN specifically in the ATR column, not the entire row.
        use_atr = self.config.exit_logic.use_atr_exit and atr_col_name in window_df.columns and not pd.isna(window_df.iloc[-1][atr_col_name])

        if use_atr:
            atr_at_signal = window_df.iloc[-1][atr_col_name]
            stop_loss_price = entry_price - (atr_at_signal * self.config.exit_logic.atr_stop_loss_multiplier)
            max_hold = self.config.exit_logic.max_holding_days

            for j in range(entry_index + 1, min(entry_index + 1 + max_hold, len(full_df))):
                if full_df.iloc[j]["Low"] <= stop_loss_price:
                    exit_date_actual = full_df.index[j]
                    exit_price = stop_loss_price
                    return exit_date_actual, exit_price

            timeout_index = min(entry_index + max_hold, len(full_df) - 1)
            exit_date_actual = full_df.index[timeout_index]
            exit_price = full_df.iloc[timeout_index]["Close"]
            log.debug(f"Max hold period triggered on {exit_date_actual.date()}")
            return exit_date_actual, exit_price
        else:  # Use legacy fixed-day exit
            exit_target_days = self.config.strategy_params.exit_days
            exit_date_target_index = entry_index + exit_target_days
            if exit_date_target_index >= len(full_df):
                exit_date_actual = full_df.index[-1]
                exit_price = full_df.iloc[-1]["Close"]
            else:
                exit_date_actual = full_df.index[exit_date_target_index]
                exit_price = full_df.iloc[exit_date_target_index]["Close"]
            return exit_date_actual, exit_price

    def _calculate_stats_from_returns(self, returns: List[float]) -> Dict[str, float | int]:
        """Calculates performance statistics from a list of returns."""
        if not returns:
            return {"win_rate": 0.0, "profit_factor": 0.0, "sample_size": 0}

        wins = [r for r in returns if r > 0.0177]  # As per PRD
        losses = [r for r in returns if r <= 0]

        win_rate = len(wins) / len(returns) if returns else 0.0
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999.0 # Avoid inf

        return {
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "sample_size": len(returns),
        }

    def _calculate_historical_stats_for_llm(self, stock: str, df: pd.DataFrame) -> Dict[str, float | int]:
        """
        Runs a lean, non-recursive backtest to gather historical stats for the LLM audit.
        This does NOT call the LLM service itself.
        """
        log.info(f"Calculating historical stats for {stock}...")
        trades: List[Trade] = []
        min_history_days = self.config.strategy_params.min_history_days

        for i in range(min_history_days, len(df) -1):
            window = df.iloc[0:i].copy()
            signal = self.signal_engine.generate_signal(window)
            if not signal:
                continue

            validation = self.validation_service.validate(window, signal)
            if not validation.is_valid:
                continue

            entry_price = df.iloc[i]["Open"]
            exit_date, exit_price = self._determine_exit(i, entry_price, df, window)

            trade = self.execution_simulator.simulate_trade(
                stock=stock,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_date=df.index[i],
                exit_date=exit_date,
                signal=signal,
                confidence_score=1.0, # Not used for historical calculation
                entry_volume=df.iloc[i]["Volume"]
            )
            if trade:
                trades.append(trade)

        returns = [t.net_return_pct for t in trades]
        return self._calculate_stats_from_returns(returns)


    def generate_opportunities(
        self, stock: str, lookback_days: int = 365
    ) -> Optional[Opportunity]:
        """
        Checks for a new trading opportunity on the most recent data for a single stock.
        This is now an efficient, non-backtesting version.
        """
        log.info(f"Checking for new opportunities for {stock}...")
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=lookback_days * 2) # Fetch more data for history

        sector_ticker = self.config.data.sector_map.get(stock)
        full_df = self.data_service.get_data(
            stock, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), sector_ticker
        )

        if full_df is None or len(full_df) < self.config.strategy_params.min_history_days:
            log.warning(f"Not enough data for {stock} to generate a signal.")
            return None

        # 1. Check for a signal on the latest data point
        latest_data_window = full_df.copy()
        signal = self.signal_engine.generate_signal(latest_data_window)
        if not signal:
            log.info(f"No preliminary signal for {stock} on the latest data.")
            return None

        # 2. Validate the signal with guardrails
        log.info(f"Preliminary signal found for {stock} on {full_df.index[-1].date()}")
        validation = self.validation_service.validate(latest_data_window, signal)
        if not validation.is_valid:
            log.info(f"Signal for {stock} rejected by guardrails: {validation.reason}")
            return None

        # 3. If valid, calculate historical stats on data *prior* to the signal
        historical_df = full_df.iloc[:-1]
        historical_stats = self._calculate_historical_stats_for_llm(stock, historical_df)
        log.info(f"Historical stats for {stock}: {historical_stats}")

        # 4. Perform LLM Audit
        confidence_score = self.llm_audit_service.get_confidence_score(
            historical_stats=historical_stats,
            signal=signal,
            df_window=latest_data_window,
        )

        if confidence_score < self.config.llm.confidence_threshold:
            log.info(
                f"Signal for {stock} rejected by LLM audit (score: {confidence_score})"
            )
            return None

        # 5. If we get here, it's a valid opportunity
        opportunity = Opportunity(
            stock=stock,
            signal_date=full_df.index[-1],
            signal=signal,
            confidence_score=confidence_score,
        )
        log.info(f"High-confidence opportunity found: {opportunity}")
        return opportunity
