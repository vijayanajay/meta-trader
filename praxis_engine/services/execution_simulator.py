"""
Service for simulating trade execution and calculating returns.
"""
from typing import Optional
import pandas as pd

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

    def calculate_net_return(self, entry_price: float, exit_price: float, volume: float) -> float:
        """
        Calculates the net return after applying the full cost model.
        This method is pure and can be used by other services.
        """
        entry_price_with_slippage = entry_price * (1 + self.cost_model.slippage_pct)
        exit_price_with_slippage = exit_price * (1 - self.cost_model.slippage_pct)

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
        This model is based on the PRD, which specifies a punitive cost structure.
        """
        # Brokerage model from PRD: max(rate * turnover, min_charge)
        brokerage = max(self.cost_model.brokerage_rate * trade_value, self.cost_model.brokerage_min)

        # STT on delivery-based equity trades as per PRD.
        stt = self.cost_model.stt_rate * trade_value
        return brokerage + stt

    def _calculate_slippage(self, entry_price: float, volume: float) -> float:
        """
        Calculates slippage based on volume.
        TODO: Implement a more sophisticated volume-based slippage model.
        For now, using a simple fixed percentage as a placeholder.
        """
        return entry_price * self.cost_model.slippage_pct

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
        entry_slippage = self._calculate_slippage(entry_price, entry_volume)
        exit_slippage = self._calculate_slippage(exit_price, 0) # Exit volume not used yet

        entry_price_with_slippage = entry_price * (1 + self.cost_model.slippage_pct)
        exit_price_with_slippage = exit_price * (1 - self.cost_model.slippage_pct)

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
