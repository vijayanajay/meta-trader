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
    """

    def __init__(self, params: StrategyParamsConfig, logic: SignalLogicConfig):
        self.params = params
        self.logic = logic

    def _prepare_dataframes(
        self, df_daily: pd.DataFrame
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
        """
        Prepares daily, weekly, and monthly dataframes with indicators.
        """
        # -- Daily Indicators --
        bb_daily = bbands(
            df_daily["Close"], length=self.params.bb_length, std=self.params.bb_std
        )
        rsi_daily = rsi(df_daily["Close"], length=self.params.rsi_length)
        df_daily = pd.concat([df_daily, bb_daily, rsi_daily], axis=1)

        # -- Weekly Indicators --
        df_weekly = df_daily.resample("W-MON").last()
        if len(df_weekly) < 10:
            return None
        bb_weekly = bbands(df_weekly["Close"], length=10, std=2.5)
        df_weekly = pd.concat([df_weekly, bb_weekly], axis=1)

        # -- Monthly Indicators --
        df_monthly = df_daily.resample("MS").last()
        if len(df_monthly) < 6:
            return None
        bb_monthly = bbands(df_monthly["Close"], length=6, std=3.0)
        df_monthly = pd.concat([df_monthly, bb_monthly], axis=1)

        return df_daily, df_weekly, df_monthly

    def generate_signal(self, full_df_with_indicators: pd.DataFrame, current_index: int | None = None) -> Optional[Signal]:
        """
        Generates a signal.

        Backwards-compatible behaviour:
        - If `current_index` is None, treat `full_df_with_indicators` as the
          original daily dataframe and run the legacy `_prepare_dataframes` path.
        - If `current_index` is provided, assume indicators are precomputed on
          the full dataframe and perform efficient lookups.
        """

        # Legacy path: caller passed only a daily df and expects _prepare_dataframes
        if current_index is None:
            df_daily = full_df_with_indicators
            if len(df_daily) < self.params.bb_length:
                return None

            prepared_data = self._prepare_dataframes(df_daily)
            if prepared_data is None:
                return None

            df_daily_prep, df_weekly, df_monthly = prepared_data

            # Check for sufficient data after resampling
            if df_daily_prep.empty or df_weekly.empty or df_monthly.empty:
                return None

            last_date = df_daily_prep.index[-1]
            latest_daily = df_daily_prep.iloc[-1]
            latest_weekly = df_weekly.asof(last_date)
            latest_monthly = df_monthly.asof(last_date)

            # After all calculations, check if the latest data points have NaNs
            if latest_daily.isnull().any() or latest_weekly.isnull().any() or latest_monthly.isnull().any():
                return None

            # Column names from our indicator functions
            bb_daily_lower_col = f"BBL_{self.params.bb_length}_{self.params.bb_std}"
            bb_daily_mid_col = f"BBM_{self.params.bb_length}_{self.params.bb_std}"
            rsi_daily_col = f"RSI_{self.params.rsi_length}"
            bb_weekly_lower_col = "BBL_10_2.5"
            bb_monthly_lower_col = "BBL_6_3.0"

            # -- Multi-frame alignment check --
            daily_oversold = latest_daily["Close"] < latest_daily[bb_daily_lower_col] and latest_daily[rsi_daily_col] < self.logic.rsi_threshold
            weekly_oversold = latest_weekly["Close"] < latest_weekly[bb_weekly_lower_col]
            monthly_not_oversold = latest_monthly["Close"] > latest_monthly[bb_monthly_lower_col]

            # Build the list of conditions based on the config
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
                    frames_aligned=["daily", "weekly"],
                    sector_vol=latest_daily["sector_vol"],
                )
                return signal

            return None

        # New, efficient path: use precomputed indicators and index-based lookup
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
            return None

        # If any of the lookup values are NaN, skip
        if pd.isna(latest_daily[bb_daily_lower_col]) or pd.isna(latest_daily[rsi_daily_col]):
            return None

        # Multi-frame alignment
        daily_oversold = latest_daily["Close"] < latest_daily[bb_daily_lower_col] and latest_daily[rsi_daily_col] < self.logic.rsi_threshold
        weekly_oversold = False
        monthly_not_oversold = False

        try:
            weekly_oversold = full_df_with_indicators.iloc[current_index]["Close"] < full_df_with_indicators.iloc[current_index][bb_weekly_lower_col]
        except Exception:
            weekly_oversold = False

        try:
            monthly_not_oversold = full_df_with_indicators.iloc[current_index]["Close"] > full_df_with_indicators.iloc[current_index][bb_monthly_lower_col]
        except Exception:
            monthly_not_oversold = False

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
                frames_aligned=["daily", "weekly"],
                sector_vol=latest_daily.get("sector_vol", 0.0),
            )
            return signal

        return None
