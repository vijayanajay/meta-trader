"""
Service for generating trading signals based on technical indicators.
"""
from typing import Optional, Tuple
import pandas as pd

from praxis_engine.core.models import Signal, StrategyParamsConfig, SignalLogicConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.indicators import bbands, rsi
from praxis_engine.core.statistics import hurst_exponent

log = get_logger(__name__)


class SignalEngine:
    """
    Generates signals based on a multi-timeframe alignment strategy.
    Assumes all indicators have been pre-computed on the dataframe.
    """

    def __init__(self, params: StrategyParamsConfig, logic: SignalLogicConfig):
        self.params = params
        self.logic = logic

    def generate_signal(self, full_df_with_indicators: pd.DataFrame, current_index: int) -> Optional[Signal]:
        """
        Generates a signal using efficient, index-based lookups on a
        dataframe with pre-computed indicators.
        """
        if current_index < self.params.bb_length:
            return None

        latest_daily = full_df_with_indicators.iloc[current_index]

        # Column names from our indicator functions
        bb_daily_lower_col = f"BBL_{self.params.bb_length}_{self.params.bb_std}"
        bb_daily_mid_col = f"BBM_{self.params.bb_length}_{self.params.bb_std}"
        rsi_daily_col = f"RSI_{self.params.rsi_length}"
        bb_weekly_lower_col = "BBL_10_2.5"
        bb_monthly_lower_col = "BBL_6_3.0"

        # Ensure required columns exist
        required_cols = [bb_daily_lower_col, bb_daily_mid_col, rsi_daily_col, "sector_vol", bb_weekly_lower_col, bb_monthly_lower_col]
        if not all(c in full_df_with_indicators.columns for c in required_cols):
            log.debug(f"Signal check skipped: missing one or more required columns.")
            return None

        # If any of the lookup values are NaN, skip
        if pd.isna(latest_daily[required_cols]).any():
            return None

        # Multi-frame alignment
        daily_oversold = latest_daily["Close"] < latest_daily[bb_daily_lower_col] and latest_daily[rsi_daily_col] < self.logic.rsi_threshold
        weekly_oversold = latest_daily["Close"] < latest_daily[bb_weekly_lower_col]
        monthly_not_oversold = latest_daily["Close"] > latest_daily[bb_monthly_lower_col]

        conditions = []
        if self.logic.require_daily_oversold:
            conditions.append(daily_oversold)
        if self.logic.require_weekly_oversold:
            conditions.append(weekly_oversold)
        if self.logic.require_monthly_not_oversold:
            conditions.append(monthly_not_oversold)

        if all(conditions):
            entry_price = latest_daily["Close"] * 1.001  # Slippage
            stop_loss = latest_daily[bb_daily_mid_col]

            signal = Signal(
                entry_price=entry_price,
                stop_loss=stop_loss,
                exit_target_days=self.params.exit_days,
                frames_aligned=["daily", "weekly", "monthly"], # Corrected
                sector_vol=latest_daily.get("sector_vol", 0.0),
            )
            return signal

        return None
