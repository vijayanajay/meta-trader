#
# main.py
#
"""
Main entry point for the Self-Improving Quant Engine.
"""
import logging
import sys

# Configure logging at the earliest point
# TODO: In a future task, this will be moved to a dedicated logging_config.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

from services import (
    ConfigService,
    StateManager,
    DataService,
    StrategyEngine,
    Backtester,
    ReportGenerator,
    LLMService,
)
from orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Initializes all services and runs the main orchestrator loop.
    """
    logger.info("Application starting.")
    try:
        # --- Service Initialization ---
        config_service = ConfigService()
        config = config_service.load_config()

        state_manager = StateManager(
            results_dir=config.app.results_dir,
            run_state_file=config.app.run_state_file,
        )
        data_service = DataService(data_dir=config.app.data_dir)
        strategy_engine = StrategyEngine()
        backtester = Backtester()
        report_generator = ReportGenerator()
        llm_service = LLMService()

        # --- Orchestrator Initialization ---
        orchestrator = Orchestrator(
            config_service=config_service,
            state_manager=state_manager,
            data_service=data_service,
            strategy_engine=strategy_engine,
            backtester=backtester,
            report_generator=report_generator,
            llm_service=llm_service,
        )

        # --- Run the main loop ---
        orchestrator.run()

    except Exception as e:
        logger.exception("A fatal error occurred. The application will now exit.")
        sys.exit(1)

    logger.info("Application finished successfully.")


if __name__ == "__main__":
    main()
