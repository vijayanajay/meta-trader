import argparse
import logging

from self_improving_quant.core.orchestrator import Orchestrator

# Basic logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main() -> None:
    """Main entry point for the CLI."""
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
