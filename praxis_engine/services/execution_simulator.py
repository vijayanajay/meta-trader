"""
Service for simulating trade execution and calculating returns.
"""
from typing import Optional
import pandas as pd
import math

from praxis_engine.core.models import Signal, Trade, CostModelConfig
from praxis_engine.core.logger import get_logger

log = get_logger(__name__)


class ExecutionSimulator:
    """
    Simulates the execution of a trade and calculates its outcome,
    including a realistic cost model. This service is pure; it does not
    have access to future data.
    """

    def __init__(self, cost_model: CostModelConfig):
        self.cost_model = cost_model

    def calculate_net_return(self, entry_price: float, exit_price: float, daily_volume: float) -> float:
        """
        Calculates the net return after applying the full cost model.
        This method is pure and can be used by other services.
        """
        # Assume exit day volume is similar to entry day for this helper
        entry_slippage = self._calculate_slippage(entry_price, daily_volume)
        exit_slippage = self._calculate_slippage(exit_price, daily_volume)

        entry_price_with_slippage = entry_price + entry_slippage
        exit_price_with_slippage = exit_price - exit_slippage

        entry_cost_per_share = self._calculate_costs(entry_price_with_slippage)
        exit_cost_per_share = self._calculate_costs(exit_price_with_slippage)

        final_entry_price = entry_price_with_slippage + entry_cost_per_share
        final_exit_price = exit_price_with_slippage - exit_cost_per_share

        if final_entry_price == 0:
            return 0.0

        return (final_exit_price / final_entry_price) - 1.0

    def _calculate_costs(self, trade_value: float) -> float:
        """
        Calculates brokerage and STT for a single transaction (entry or exit).
        This model is based on the PRD, which specifies a Zerodha-like cost structure.
        """
        # Brokerage model from PRD: min(rate * turnover, max_charge)
        brokerage = min(self.cost_model.brokerage_rate * trade_value, self.cost_model.brokerage_max)

        # STT on delivery-based equity trades as per PRD.
        stt = self.cost_model.stt_rate * trade_value
        return brokerage + stt

    def _calculate_slippage(self, price: float, daily_volume: float) -> float:
        """
        Calculates the slippage cost per share based on a market impact model.

        Slippage is modeled as a function of the trade's size relative to the
        total daily volume, making it non-linear.

        Args:
            price: The execution price before slippage.
            daily_volume: The total traded volume for the day.

        Returns:
            The estimated slippage cost per share.
        """
        if daily_volume == 0 or price == 0:
            # Cannot execute if there is no volume or price, return a large slippage
            # to make the trade unprofitable.
            return price

        # TODO: Replace assumed trade value with actual position size when available
        trade_volume = self.cost_model.assumed_trade_value_inr / price

        # Ensure trade volume does not exceed daily volume
        if trade_volume > daily_volume:
            trade_volume = daily_volume

        volume_share = trade_volume / daily_volume

        # Slippage pct is a function of the share of volume traded.
        # Using a square root to make the impact less extreme.
        slippage_pct = self.cost_model.slippage_impact_factor * math.sqrt(volume_share)

        return price * slippage_pct

    def simulate_trade(
        self,
        stock: str,
        entry_price: float,
        exit_price: float,
        entry_date: pd.Timestamp,
        exit_date: pd.Timestamp,
        signal: Signal,
        confidence_score: float,
        entry_volume: float,
    ) -> Optional[Trade]:
        """
        Simulates a single trade based on known entry and exit points.
        This method is pure and has no access to data beyond what is provided.
        """
        # --- Cost Model Application ---
        # TODO: The Orchestrator should provide the exit day's volume.
        # For now, using entry volume as a proxy for exit volume slippage calculation.
        entry_slippage = self._calculate_slippage(entry_price, entry_volume)
        exit_slippage = self._calculate_slippage(exit_price, entry_volume)

        entry_price_with_slippage = entry_price + entry_slippage
        exit_price_with_slippage = exit_price - exit_slippage

        # Costs are calculated based on the price per share
        entry_cost_per_share = self._calculate_costs(entry_price_with_slippage)
        exit_cost_per_share = self._calculate_costs(exit_price_with_slippage)

        # The final entry price is adjusted for costs
        final_entry_price = entry_price_with_slippage + entry_cost_per_share
        final_exit_price = exit_price_with_slippage - exit_cost_per_share

        # Calculate net return after all costs and slippage
        if final_entry_price == 0:
            return None

        net_return_pct = (final_exit_price / final_entry_price) - 1.0

        log.info(f"Trade for {stock} on {entry_date}: Entry={entry_price:.2f}, Exit={exit_price:.2f}, Slippage={entry_slippage:.2f}, Net Return={net_return_pct:.2%}")

        return Trade(
            stock=stock,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            net_return_pct=net_return_pct,
            confidence_score=confidence_score,
            signal=signal,
        )
