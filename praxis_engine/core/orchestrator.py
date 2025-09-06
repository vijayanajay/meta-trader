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
from praxis_engine.services.execution_simulator import ExecutionSimulator
from praxis_engine.core.logger import get_logger
from praxis_engine.utils import get_nested_attr, set_nested_attr

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
                # Find the guard that produced the lowest score to attribute the rejection.
                # We exclude 'composite_score' itself from this calculation.
                individual_scores = {
                    k: v for k, v in scores.model_dump().items() if k != 'composite_score'
                }
                # Find the key corresponding to the minimum value in the filtered dict
                rejection_reason_key = min(individual_scores, key=individual_scores.get)
                guard_name = f"{rejection_reason_key.split('_')[0].capitalize()}Guard"
                metrics.rejections_by_guard[guard_name] += 1
                continue

            # LLM audit is removed from the core pipeline. A default confidence of 1.0 is passed.
            trade = self._simulate_trade_from_signal(
                df=full_df,
                signal_index=current_index,
                signal=signal,
                stock=stock,
                confidence=1.0,
                scores=scores,
            )
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

    def _simulate_trade_from_signal(
        self,
        *,
        df: pd.DataFrame,
        signal_index: int,
        signal: Signal,
        stock: str,
        confidence: float,
        scores: ValidationScores,
    ) -> Optional[Trade]:
        """Determines exit and simulates a single trade from a validated signal."""
        entry_index = signal_index + 1
        entry_price = df.iloc[entry_index]["Open"]
        entry_volume = df.iloc[entry_index]["Volume"]
        entry_date = df.index[entry_index]

        exit_date, exit_price, exit_reason = self._determine_exit(
            entry_index, entry_price, df, df.iloc[0:entry_index]
        )

        if exit_date is None or exit_price is None:
            return None

        # --- Gather all data for the enriched Trade object ---
        strat_params = self.config.strategy_params
        exit_logic = self.config.exit_logic

        hurst_col = f"hurst_{strat_params.hurst_length}"
        adf_col = "adf_p_value"

        signal_row = df.iloc[signal_index]
        entry_hurst = signal_row.get(hurst_col, np.nan)
        entry_adf_p_value = signal_row.get(adf_col, np.nan)

        return self.execution_simulator.simulate_trade(
            stock=stock,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=entry_date,
            exit_date=exit_date,
            signal=signal,
            confidence_score=confidence,
            entry_volume=entry_volume,
            exit_reason=exit_reason,
            liquidity_score=scores.liquidity_score,
            regime_score=scores.regime_score,
            stat_score=scores.stat_score,
            composite_score=scores.composite_score,
            entry_hurst=entry_hurst,
            entry_adf_p_value=entry_adf_p_value,
            entry_sector_vol=signal.sector_vol,
            config_bb_length=strat_params.bb_length,
            config_rsi_length=strat_params.rsi_length,
            config_atr_multiplier=exit_logic.atr_stop_loss_multiplier,
        )

    def _determine_exit(
        self, entry_index: int, entry_price: float, full_df: pd.DataFrame, window_df: pd.DataFrame
    ) -> Tuple[Optional[pd.Timestamp], Optional[float], str]:
        """
        Determines the exit date and price for a trade based on a hierarchy of exit conditions.
        Returns the exit date, exit price, and the reason for the exit.
        """
        exit_logic = self.config.exit_logic

        # 1. ATR Stop-Loss and Profit Target
        atr_col_name = f"ATR_{exit_logic.atr_period}"
        use_atr = (
            exit_logic.use_atr_exit
            and atr_col_name in window_df.columns
            and not pd.isna(window_df.iloc[-1][atr_col_name])
        )
        stop_loss_price = None
        profit_target_price = None

        if use_atr:
            atr_at_signal = window_df.iloc[-1][atr_col_name]
            stop_loss_price = entry_price - (atr_at_signal * exit_logic.atr_stop_loss_multiplier)
            risk_per_share = entry_price - stop_loss_price
            profit_target_price = entry_price + (
                risk_per_share * exit_logic.reward_risk_ratio
            )

        max_hold = exit_logic.max_holding_days
        for j in range(entry_index + 1, min(entry_index + 1 + max_hold, len(full_df))):
            current_day = full_df.iloc[j]

            # Priority 1: Check for ATR Stop-Loss
            if stop_loss_price and current_day["Low"] <= stop_loss_price:
                log.debug(f"ATR stop-loss triggered on {current_day.name.date()}")
                return current_day.name, stop_loss_price, "ATR_STOP_LOSS"

            # Priority 2: Check for Fixed Profit Target
            if profit_target_price and current_day["High"] >= profit_target_price:
                log.debug(f"Fixed profit target hit on {current_day.name.date()}")
                return current_day.name, profit_target_price, "PROFIT_TARGET"

        # Priority 3: Max Holding Period Timeout
        timeout_index = min(entry_index + max_hold, len(full_df) - 1)
        exit_date = full_df.index[timeout_index]
        exit_price = full_df.iloc[timeout_index]["Close"]
        log.debug(f"Max hold period triggered on {exit_date.date()}")
        return exit_date, exit_price, "MAX_HOLD_TIMEOUT"

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
                        trade = self._simulate_trade_from_signal(
                            df=df,
                            signal_index=i,
                            signal=signal,
                            stock="HISTORICAL",
                            confidence=1.0,
                            scores=scores,
                        )
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

        # LLM audit is removed from the core pipeline. A default confidence of 1.0 is used.
        opportunity = Opportunity(
            stock=stock,
            signal_date=full_df.index[-1],
            signal=signal,
            confidence_score=1.0,
        )
        log.info(f"High-confidence opportunity found: {opportunity}")
        return opportunity

