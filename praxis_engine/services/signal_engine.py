"""
Service for generating trading signals based on technical indicators.
"""
from typing import Optional
import pandas as pd

from praxis_engine.core.models import Signal, StrategyParamsConfig
from praxis_engine.core.logger import get_logger
from praxis_engine.core.indicators import bbands, rsi

log = get_logger(__name__)

class SignalEngine:
    """
    Generates signals based on a multi-timeframe alignment strategy.
    """

    def __init__(self, params: StrategyParamsConfig):
        self.params = params

    def generate_signal(self, df_daily: pd.DataFrame) -> Optional[Signal]:
        """
        Generates a signal based on Bollinger Band and RSI alignment
        across daily, weekly, and monthly timeframes.
        """
        if len(df_daily) < self.params.bb_length:
            return None

        # -- Daily Indicators --
        bb_daily = bbands(df_daily["Close"], length=self.params.bb_length, std=self.params.bb_std)
        rsi_daily = rsi(df_daily["Close"], length=self.params.rsi_length)
        df_daily = pd.concat([df_daily, bb_daily, rsi_daily], axis=1)

        # -- Weekly Indicators --
        df_weekly = df_daily.resample('W-FRI').last().dropna()
        if len(df_weekly) < 10: return None # Check length after dropna
        bb_weekly = bbands(df_weekly["Close"], length=10, std=2.5)
        df_weekly = pd.concat([df_weekly, bb_weekly], axis=1)

        # -- Monthly Indicators --
        df_monthly = df_daily.resample('ME').last().dropna()
        if len(df_monthly) < 6: return None # Check length after dropna
        bb_monthly = bbands(df_monthly["Close"], length=6, std=3.0)
        df_monthly = pd.concat([df_monthly, bb_monthly], axis=1)

        # Check for sufficient data after resampling
        if df_daily.empty or df_weekly.empty or df_monthly.empty:
            return None

        latest_daily = df_daily.iloc[-1]
        latest_weekly = df_weekly.iloc[-1]
        latest_monthly = df_monthly.iloc[-1]

        # Column names from our indicator functions
        bb_daily_lower_col = f"BBL_{self.params.bb_length}_{self.params.bb_std}"
        bb_daily_mid_col = f"BBM_{self.params.bb_length}_{self.params.bb_std}"
        rsi_daily_col = f"RSI_{self.params.rsi_length}"
        bb_weekly_lower_col = "BBL_10_2.5"
        bb_monthly_lower_col = "BBL_6_3.0"

        # -- Multi-frame alignment check --
        daily_oversold = latest_daily["Close"] < latest_daily[bb_daily_lower_col] and latest_daily[rsi_daily_col] < 35
        weekly_oversold = latest_weekly["Close"] < latest_weekly[bb_weekly_lower_col]
        monthly_not_oversold = latest_monthly["Close"] > latest_monthly[bb_monthly_lower_col]

        if daily_oversold and weekly_oversold and monthly_not_oversold:
            entry_price = latest_daily["Close"] * 1.001  # Slippage
            stop_loss = latest_daily[bb_daily_mid_col]

            signal = Signal(
                entry_price=entry_price,
                stop_loss=stop_loss,
                exit_target_days=self.params.exit_days,
                frames_aligned=["daily", "weekly"],
                sector_vol=latest_daily["sector_vol"]
            )
            log.info(f"Signal generated: {signal}")
            return signal

        return None
