"""
The main orchestrator for running backtests.
"""
import copy
from typing import List, Dict
import pandas as pd
import numpy as np


import datetime
from typing import Optional, Any, Tuple

from praxis_engine.core.indicators import atr
from praxis_engine.core.models import BacktestMetrics, BacktestSummary, Config, Trade, Opportunity
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
        self.validation_service = ValidationService(config.scoring, config.strategy_params)
        self.execution_simulator = ExecutionSimulator(config.cost_model)
        self.llm_audit_service = LLMAuditService(config.llm)

    def run_backtest(self, stock: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Runs a walk-forward backtest for a single stock.

        Returns:
            A dictionary containing the list of trades and the backtest metrics.
        """
        log.debug(f"Starting backtest for {stock} from {start_date} to {end_date}...")
        metrics = BacktestMetrics()

        sector_ticker = self.config.data.sector_map.get(stock)
        full_df = self.data_service.get_data(stock, start_date, end_date, sector_ticker)

        if full_df is None or full_df.empty:
            log.warning(f"No data found for {stock}. Skipping backtest.")
            return {"trades": [], "metrics": metrics}

        trades: List[Trade] = []
        min_history_days = self.config.strategy_params.min_history_days
        atr_col_name = f"ATR_{self.config.exit_logic.atr_period}"

        for i in range(min_history_days, len(full_df) - 1):  # -1 to ensure there's a next day for entry
            window = full_df.iloc[0:i].copy()
            signal_date = window.index[-1]

            if self.config.exit_logic.use_atr_exit:
                atr_series = atr(window["High"], window["Low"], window["Close"], length=self.config.exit_logic.atr_period)
                if atr_series is not None:
                    window[atr_col_name] = atr_series
                    window[atr_col_name] = window[atr_col_name].bfill()

            signal = self.signal_engine.generate_signal(window)
            if not signal:
                continue

            metrics.potential_signals += 1
            log.debug(f"Preliminary signal found for {stock} on {signal_date.date()}")

            scores = self.validation_service.validate(window, signal)
            composite_score = scores.liquidity_score * scores.regime_score * scores.stat_score

            if composite_score < self.config.llm.min_composite_score_for_llm:
                log.debug(f"Signal for {stock} rejected by pre-filter. Composite score: {composite_score:.2f}")
                # Determine the primary reason for rejection
                scores_dict = scores.model_dump()
                rejection_reason = min(scores_dict, key=lambda k: scores_dict[k])
                guard_name = f"{rejection_reason.split('_')[0].capitalize()}Guard"
                metrics.rejections_by_guard[guard_name] = metrics.rejections_by_guard.get(guard_name, 0) + 1
                continue

            log.debug(f"Validated signal found for {stock} on {signal_date.date()} with composite score {composite_score:.2f}")

            # Calculate historical stats on all data *prior* to the current signal.
            # This prevents lookahead bias.
            historical_df = full_df.iloc[0:i-1]
            historical_stats = self._calculate_historical_stats_for_llm(stock, historical_df)

            if self.config.llm.use_llm_audit:
                confidence_score = self.llm_audit_service.get_confidence_score(
                    historical_stats=historical_stats,
                    signal=signal,
                    df_window=window,
                )
            else:
                confidence_score = 1.0  # Bypass LLM audit with max confidence
                log.debug("LLM audit is disabled. Assigning default confidence score of 1.0.")

            if confidence_score < self.config.llm.confidence_threshold:
                log.debug(f"Signal for {stock} rejected by LLM audit (score: {confidence_score})")
                metrics.rejections_by_llm += 1
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
                log.debug(f"Trade simulated: {trade}")
                trades.append(trade)
                metrics.trades_executed += 1

        log.debug(f"Backtest for {stock} complete. Found {len(trades)} trades.")
        return {"trades": trades, "metrics": metrics}

    def _determine_exit(self, entry_index: int, entry_price: float, full_df: pd.DataFrame, window_df: pd.DataFrame) -> Tuple[pd.Timestamp, float]:
        """ Determines the exit date and price for a trade. """
        atr_col_name = f"ATR_{self.config.exit_logic.atr_period}"
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

        wins = [r for r in returns if r > 0.0177]
        losses = [r for r in returns if r <= 0]

        win_rate = len(wins) / len(returns) if returns else 0.0
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999.0

        return {
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "sample_size": len(returns),
        }

    def _calculate_historical_stats_for_llm(self, stock: str, df: pd.DataFrame) -> Dict[str, float | int]:
        """
        Runs a lean, non-recursive backtest to gather historical stats for the LLM audit.
        """
        log.info(f"Calculating historical stats for {stock}...")
        trades: List[Trade] = []
        min_history_days = self.config.strategy_params.min_history_days

        for i in range(min_history_days, len(df) -1):
            window = df.iloc[0:i].copy()
            signal = self.signal_engine.generate_signal(window)
            if not signal:
                continue

            scores = self.validation_service.validate(window, signal)
            composite_score = scores.liquidity_score * scores.regime_score * scores.stat_score
            if composite_score < self.config.llm.min_composite_score_for_llm:
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
                confidence_score=1.0,
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
        """
        log.info(f"Checking for new opportunities for {stock}...")
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=lookback_days * 2)

        sector_ticker = self.config.data.sector_map.get(stock)
        full_df = self.data_service.get_data(
            stock, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), sector_ticker
        )

        if full_df is None or len(full_df) < self.config.strategy_params.min_history_days:
            log.warning(f"Not enough data for {stock} to generate a signal.")
            return None

        latest_data_window = full_df.copy()
        signal = self.signal_engine.generate_signal(latest_data_window)
        if not signal:
            log.info(f"No preliminary signal for {stock} on the latest data.")
            return None

        log.debug(f"Preliminary signal found for {stock} on {full_df.index[-1].date()}")
        scores = self.validation_service.validate(latest_data_window, signal)
        composite_score = scores.liquidity_score * scores.regime_score * scores.stat_score

        if composite_score < self.config.llm.min_composite_score_for_llm:
            log.debug(f"Signal for {stock} rejected by pre-filter. Composite score: {composite_score:.2f}")
            return None

        historical_df = full_df.iloc[:-1]
        historical_stats = self._calculate_historical_stats_for_llm(stock, historical_df)
        log.debug(f"Historical stats for {stock}: {historical_stats}")

        if self.config.llm.use_llm_audit:
            confidence_score = self.llm_audit_service.get_confidence_score(
                historical_stats=historical_stats,
                signal=signal,
                df_window=latest_data_window,
            )
        else:
            confidence_score = 1.0 # Bypass LLM audit with max confidence
            log.debug("LLM audit is disabled. Assigning default confidence score of 1.0.")

        if confidence_score < self.config.llm.confidence_threshold:
            log.debug(f"Signal for {stock} rejected by LLM audit (score: {confidence_score})")
            return None

        opportunity = Opportunity(
            stock=stock,
            signal_date=full_df.index[-1],
            signal=signal,
            confidence_score=confidence_score,
        )
        log.info(f"High-confidence opportunity found: {opportunity}")
        return opportunity

    def run_sensitivity_analysis(self) -> List[BacktestSummary]:
        """
        Runs multiple backtests to analyze the sensitivity of a parameter.
        """
        if not self.config.sensitivity_analysis:
            log.error("Sensitivity analysis section not found in config.")
            return []

        sa_config = self.config.sensitivity_analysis
        param_name = sa_config.parameter_to_vary
        start = sa_config.start_value
        end = sa_config.end_value
        step = sa_config.step_size

        log.info(f"Starting sensitivity analysis for '{param_name}' from {start} to {end} with step {step}")

        results: List[BacktestSummary] = []
        for value_np in np.arange(start, end + step, step):
            value = float(value_np)
            log.info(f"Running backtest with {param_name} = {value:.4f}")

            # Define the type of final_value to satisfy mypy for the conditional assignment
            final_value: float | int = value
            if param_name in ['strategy_params.bb_length', 'strategy_params.rsi_length',
                            'strategy_params.hurst_length', 'strategy_params.exit_days',
                            'strategy_params.min_history_days', 'strategy_params.liquidity_lookback_days',
                            'exit_logic.atr_period', 'exit_logic.max_holding_days']:
                final_value = int(value)

            # This is a critical change for efficiency. Instead of creating a new
            # Orchestrator for each loop, we temporarily modify the config of the
            # existing one. This avoids the overhead of re-initializing all services.
            original_value = _get_nested_attr(self.config, param_name)
            _set_nested_attr(self.config, param_name, final_value)

            all_trades: List[Trade] = []
            # Metrics are not yet used in sensitivity analysis report, but we handle them
            # to align with the new run_backtest signature.
            for stock in self.config.data.stocks_to_backtest:
                result = self.run_backtest(
                    stock, self.config.data.start_date, self.config.data.end_date
                )
                all_trades.extend(result["trades"])

            # Restore the original config value to ensure the orchestrator is in a
            # clean state after the analysis.
            _set_nested_attr(self.config, param_name, original_value)

            summary = self._aggregate_trades(all_trades, value)
            results.append(summary)
            log.info(f"Summary for {param_name} = {value:.4f}: {summary.total_trades} trades")

        return results

    def _aggregate_trades(self, trades: List[Trade], param_value: float) -> BacktestSummary:
        """
        Aggregates a list of trades into a BacktestSummary object.
        """
        if not trades:
            return BacktestSummary(
                parameter_value=param_value,
                total_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                net_return_pct_mean=0.0,
                net_return_pct_std=0.0
            )

        returns = [t.net_return_pct for t in trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        win_rate = len(wins) / len(trades) if trades else 0.0
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999.0

        return BacktestSummary(
            parameter_value=param_value,
            total_trades=len(trades),
            win_rate_pct=win_rate * 100,
            profit_factor=profit_factor,
            net_return_pct_mean=float(np.mean(returns)) * 100,
            net_return_pct_std=float(np.std(returns)) * 100
        )


import functools

def _get_nested_attr(obj: Any, attr_string: str) -> Any:
    """
    Gets a nested attribute from an object based on a dot-separated string.
    """
    return functools.reduce(getattr, attr_string.split('.'), obj)


def _set_nested_attr(obj: Any, attr_string: str, value: Any) -> None:
    """
    Sets a nested attribute on an object based on a dot-separated string.
    """
    attrs = attr_string.split('.')
    parent = functools.reduce(getattr, attrs[:-1], obj)
    setattr(parent, attrs[-1], value)
