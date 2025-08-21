import argparse
import logging

from self_improving_quant.core.orchestrator import Orchestrator
from self_improving_quant.utils.logging_config import setup_logging


def main() -> None:
    """Main entry point for the CLI."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Self-Improving Quant Engine")
    parser.add_argument("--ticker", type=str, default="RELIANCE.NS", help="Stock ticker to trade.")
    parser.add_argument("--iterations", type=int, default=5, help="Number of improvement iterations.")
    args = parser.parse_args()

    try:
        orchestrator = Orchestrator(ticker=args.ticker, num_iterations=args.iterations)
        orchestrator.run()
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
