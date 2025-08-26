"""
Service for simulating trade execution and calculating returns.
"""
from typing import Optional
import pandas as pd

from praxis_engine.core.models import Signal, Trade
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class ExecutionSimulator:
    """
    Simulates the execution of a trade and calculates its outcome,
    including a realistic cost model.
    """

    def _calculate_costs(self, trade_value: float) -> float:
        """
        Calculates brokerage and STT for a single transaction (entry or exit).
        This is a simplified model. A real one might include more fee types.
        """
        # Zerodha-like model: 0.03% of turnover or Rs. 20, whichever is lower
        # For simplicity, we use a fixed max of Rs. 20 as a proxy.
        brokerage = min(0.0003 * trade_value, 20)
        # STT on delivery-based equity trades is 0.1% on both buy and sell
        stt = 0.001 * trade_value
        # Other charges (exchange transaction, stamp duty, etc.) are ignored for now.
        return brokerage + stt

    def simulate_trade(
        self,
        stock: str,
        entry_window: pd.DataFrame,
        full_data: pd.DataFrame,
        signal: Signal,
        confidence_score: float,
    ) -> Optional[Trade]:
        """
        Simulates a single trade based on a signal, without looking into the future
        for the trade logic itself. The exit price is determined from the full_data
        for simulation purposes only.
        """
        entry_date = entry_window.index[-1]

        # To get the entry price for the next day's open, we need to find the date in the full dataset
        try:
            entry_price = full_data.loc[entry_date + pd.Timedelta(days=1)]["Open"]
        except KeyError:
            # The next day might be a holiday, find the next valid trading day
            next_day_slice = full_data.loc[entry_date:]
            if len(next_day_slice) < 2:
                log.warning(f"Not enough data to determine entry price for signal on {entry_date}")
                return None
            entry_price = next_day_slice.iloc[1]["Open"]


        # Determine exit date. This is for simulation, not for the strategy decision.
        exit_date = entry_date + pd.Timedelta(days=signal.exit_target_days)
        if exit_date > full_data.index[-1]:
            exit_date = full_data.index[-1]

        # Find the actual exit date in the dataframe (in case of holidays)
        try:
            exit_price = full_data.loc[exit_date]["Close"]
        except KeyError:
            # The target exit date is a holiday, get the last available price before it
            exit_price = full_data.asof(exit_date)["Close"]


        # --- Cost Model Application ---
        entry_value = entry_price
        exit_value = exit_price

        entry_costs = self._calculate_costs(entry_value)
        exit_costs = self._calculate_costs(exit_value)

        # Slippage: Assume a simple fixed percentage for now.
        # This should be a function of liquidity in a more advanced model.
        slippage_pct = 0.001 # 0.1%
        entry_price_with_slippage = entry_price * (1 + slippage_pct)
        exit_price_with_slippage = exit_price * (1 - slippage_pct)

        # Calculate net return after all costs and slippage
        net_return_pct = (
            (exit_price_with_slippage - exit_costs) / (entry_price_with_slippage + entry_costs)
        ) - 1.0

        log.info(f"Trade for {stock} on {entry_date}: Entry={entry_price:.2f}, Exit={exit_price:.2f}, Net Return={net_return_pct:.2%}")

        return Trade(
            stock=stock,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            net_return_pct=net_return_pct,
            confidence_score=confidence_score,
        )
