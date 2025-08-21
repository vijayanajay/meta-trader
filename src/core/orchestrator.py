"""
The Orchestrator component that manages the main feedback loop.
"""
from typing import TYPE_CHECKING
from core.models import Config

# This block is only evaluated by type checkers, not at runtime.
# It avoids circular import errors.
if TYPE_CHECKING:
    from services import (
        StateManager,
        DataService,
        StrategyEngine,
        Backtester,
        ReportGenerator,
        LLMService,
    )

__all__ = ["Orchestrator"]


class Orchestrator:
    """
    Manages the end-to-end process of running the optimization loop.
    """
    def __init__(
        self,
        config: Config,
        # Use string forward references for type hints
        state_manager: "StateManager",
        data_service: "DataService",
        strategy_engine: "StrategyEngine",
        backtester: "Backtester",
        report_generator: "ReportGenerator",
        llm_service: "LLMService",
    ):
        self._config = config
        self._state_manager = state_manager
        self._data_service = data_service
        self._strategy_engine = strategy_engine
        self._backtester = backtester
        self._report_generator = report_generator
        self._llm_service = llm_service

    def run(self) -> None:
        """
        Executes the main optimization loop for each ticker.
        """
        print("Orchestrator run initiated.")
        print(f"Configuration loaded for tickers: {self._config.app.tickers}")
        # This is a placeholder implementation.
        pass
