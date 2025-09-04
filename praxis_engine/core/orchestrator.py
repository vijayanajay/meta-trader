"""
The main orchestrator for running backtests.
"""
import copy
from typing import List, Dict
import pandas as pd
import numpy as np


import datetime
from typing import Optional, Any, Tuple

from praxis_engine.core.indicators import atr, bbands, rsi
from praxis_engine.core.statistics import hurst_exponent, adf_test
from praxis_engine.core.precompute import precompute_indicators
from praxis_engine.core.models import (
    BacktestMetrics,
    BacktestSummary,
    Config,
    Trade,
    Opportunity,
    Signal,
    ValidationScores,
)
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

        try:
            full_df = precompute_indicators(full_df, self.config)
            full_df = self._pre_calculate_historical_performance(full_df)
        except Exception as e:
            log.error(f"Precomputation failed for {stock}: {e}", exc_info=True)
            return {"trades": [], "metrics": metrics}

        for i in range(min_history_days, len(full_df) - 1):
            current_index = i - 1
            signal_date = full_df.index[current_index]

            validated_signal = self._get_validated_signal(full_df, current_index, stock)
            if not validated_signal:
                continue

            signal, scores = validated_signal
            metrics.potential_signals += 1

            if scores.composite_score < self.config.llm.min_composite_score_for_llm:
                rejection_reason = min(scores.model_dump(), key=lambda k: scores.model_dump()[k])
                guard_name = f"{rejection_reason.split('_')[0].capitalize()}Guard"
                metrics.rejections_by_guard[guard_name] += 1
                continue

            historical_stats = {
                "win_rate": full_df.at[signal_date, "hist_win_rate"],
                "profit_factor": full_df.at[signal_date, "hist_profit_factor"],
                "sample_size": full_df.at[signal_date, "hist_sample_size"],
            }

            confidence_score = self.llm_audit_service.get_confidence_score(
                historical_stats=historical_stats,
                signal=signal,
                df_window=full_df.iloc[0:i]
            ) if self.config.llm.use_llm_audit else 1.0

            if confidence_score < self.config.llm.confidence_threshold:
                metrics.rejections_by_llm += 1
                continue

            trade = self._simulate_trade_from_signal(full_df, current_index, signal, stock, confidence_score)
            if trade:
                trades.append(trade)
                metrics.trades_executed += 1

        log.debug(f"Backtest for {stock} complete. Found {len(trades)} trades.")
        return {"trades": trades, "metrics": metrics}

    def _get_validated_signal(self, df: pd.DataFrame, index: int, stock: str) -> Optional[Tuple[Signal, ValidationScores]]:
        """Generates and validates a signal for a given point in time."""
        signal = self.signal_engine.generate_signal(df, index)
        if not signal:
            return None

        log.debug(f"Preliminary signal found for {stock} on {df.index[index].date()}")
        scores = self.validation_service.validate(df, index, signal)
        return signal, scores

    def _simulate_trade_from_signal(self, df: pd.DataFrame, signal_index: int, signal: Signal, stock: str, confidence: float) -> Optional[Trade]:
        """Determines exit and simulates a single trade from a validated signal."""
        entry_index = signal_index + 1
        entry_price = df.iloc[entry_index]["Open"]
        entry_volume = df.iloc[entry_index]["Volume"]
        entry_date = df.index[entry_index]

        exit_date, exit_price = self._determine_exit(entry_index, entry_price, df, df.iloc[0:entry_index])

        if exit_date is None or exit_price is None:
            return None

        return self.execution_simulator.simulate_trade(
            stock=stock,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=entry_date,
            exit_date=exit_date,
            signal=signal,
            confidence_score=confidence,
            entry_volume=entry_volume
        )

    def _determine_exit(self, entry_index: int, entry_price: float, full_df: pd.DataFrame, window_df: pd.DataFrame) -> Tuple[Optional[pd.Timestamp], Optional[float]]:
        """ Determines the exit date and price for a trade. """
        atr_col_name = f"ATR_{self.config.exit_logic.atr_period}"
        use_atr = self.config.exit_logic.use_atr_exit and atr_col_name in window_df.columns and not pd.isna(window_df.iloc[-1][atr_col_name])

        if use_atr:
            atr_at_signal = window_df.iloc[-1][atr_col_name]
            stop_loss_price = entry_price - (atr_at_signal * self.config.exit_logic.atr_stop_loss_multiplier)
            max_hold = self.config.exit_logic.max_holding_days

            for j in range(entry_index + 1, min(entry_index + 1 + max_hold, len(full_df))):
                if full_df.iloc[j]["Low"] <= stop_loss_price:
                    return full_df.index[j], stop_loss_price

            timeout_index = min(entry_index + max_hold, len(full_df) - 1)
            log.debug(f"Max hold period triggered on {full_df.index[timeout_index].date()}")
            return full_df.index[timeout_index], full_df.iloc[timeout_index]["Close"]
        else:  # Use legacy fixed-day exit
            exit_target_days = self.config.strategy_params.exit_days
            exit_date_target_index = entry_index + exit_target_days
            if exit_date_target_index >= len(full_df):
                return full_df.index[-1], full_df.iloc[-1]["Close"]
            else:
                return full_df.index[exit_date_target_index], full_df.iloc[exit_date_target_index]["Close"]

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

    def _pre_calculate_historical_performance(self, df_with_indicators: pd.DataFrame) -> pd.DataFrame:
        """
        Performs a single-pass simulation to calculate historical performance statistics
        in a point-in-time correct way, avoiding lookahead bias.
        """
        df = df_with_indicators.copy()
        df["hist_win_rate"] = np.nan
        df["hist_profit_factor"] = np.nan
        df["hist_sample_size"] = np.nan

        min_history_days = self.config.strategy_params.min_history_days
        trades_in_flight: List[Trade] = []
        historical_returns: List[float] = []

        for i in range(len(df)):
            today = df.index[i]

            exited_trades_returns = [t.net_return_pct for t in trades_in_flight if t.exit_date.normalize() == today.normalize()]
            if exited_trades_returns:
                historical_returns.extend(exited_trades_returns)
                trades_in_flight = [t for t in trades_in_flight if t.exit_date.normalize() != today.normalize()]

            if i >= min_history_days:
                stats = self._calculate_stats_from_returns(historical_returns)
                df.loc[today, "hist_win_rate"] = stats["win_rate"]
                df.loc[today, "hist_profit_factor"] = stats["profit_factor"]
                df.loc[today, "hist_sample_size"] = stats["sample_size"]

            if i >= min_history_days and i < len(df) - 1:
                validated_signal = self._get_validated_signal(df, i, "HISTORICAL")
                if validated_signal:
                    signal, scores = validated_signal
                    if scores.composite_score >= self.config.llm.min_composite_score_for_llm:
                        trade = self._simulate_trade_from_signal(df, i, signal, "HISTORICAL", 1.0)
                        if trade:
                            trades_in_flight.append(trade)
        return df

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
        current_index = len(full_df) - 1
        signal = self.signal_engine.generate_signal(full_df, current_index)
        if not signal:
            log.info(f"No preliminary signal for {stock} on the latest data.")
            return None

        log.debug(f"Preliminary signal found for {stock} on {full_df.index[-1].date()}")
        scores = self.validation_service.validate(full_df, current_index, signal)
        composite_score = scores.liquidity_score * scores.regime_score * scores.stat_score

        if composite_score < self.config.llm.min_composite_score_for_llm:
            log.debug(f"Signal for {stock} rejected by pre-filter. Composite score: {composite_score:.2f}")
            return None

        # Precompute indicators and historical performance
        full_df = precompute_indicators(full_df, self.config)
        full_df = self._pre_calculate_historical_performance(full_df)

        historical_stats = {
            "win_rate": full_df.iloc[-1]["hist_win_rate"],
            "profit_factor": full_df.iloc[-1]["hist_profit_factor"],
            "sample_size": full_df.iloc[-1]["hist_sample_size"],
        }
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
