"""
Core command functions for the Praxis Engine CLI.
"""
import datetime
from pathlib import Path
import pandas as pd
import typer

from praxis_engine.core.logger import get_logger
from praxis_engine.services.config_service import load_config

log = get_logger(__name__)


def verify_config(config_path: str) -> None:
    """
    Loads and verifies the configuration file.
    """
    log.info("Attempting to load configuration...")
    try:
        config = load_config(config_path)
        log.info("Configuration loaded and validated successfully!")
        log.info(config)
    except Exception as e:
        log.error(f"Error loading configuration: {e}")
        raise typer.Exit(code=1)


def backtest(config_path: str) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    from praxis_engine.core.orchestrator import Orchestrator
    from praxis_engine.services.report_generator import ReportGenerator

    log.info("Loading configuration...")
    config = load_config(config_path)

    orchestrator = Orchestrator(config)

    all_trades = []
    for stock in config.data.stocks_to_backtest:
        trades = orchestrator.run_backtest(
            stock, config.data.start_date, config.data.end_date
        )
        all_trades.extend(trades)

    if all_trades:
        log.info(f"Backtest complete. Total trades executed: {len(all_trades)}")
        report_generator = ReportGenerator()
        report = report_generator.generate_backtest_report(
            all_trades, config.data.start_date, config.data.end_date
        )

        # Save the report
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        report_path = results_dir / "backtest_summary.md"

        with open(report_path, "w") as f:
            f.write(report)

        log.info(f"Backtest report saved to {report_path}")
        log.info("\n" + report)
    else:
        log.info("Backtest complete. No trades were executed.")


def generate_report(config_path: str) -> None:
    """
    Runs the engine on the latest data to find new opportunities.
    """
    from praxis_engine.core.orchestrator import Orchestrator

    log.info("Loading configuration...")
    config = load_config(config_path)

    orchestrator = Orchestrator(config)

    # For weekly report, we are interested in the latest signals.
    # We run the "backtest" but only care about signals from the last few days.
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=365 * 5)).strftime(
        "%Y-%m-%d"
    )  # 5 years of data for context

    all_opportunities = []

    for stock in config.data.stocks_to_backtest:
        # This is a simplified approach. A more robust implementation would have a dedicated
        # "live" run mode in the orchestrator.
        trades = orchestrator.run_backtest(stock, start_date, end_date)
        if trades:
            # For this report, we only care about the most recent trade signal
            last_trade = trades[-1]
            # Check if the signal is recent (e.g., within the last 7 days)
            if (pd.Timestamp.today() - last_trade.entry_date).days <= 7:
                all_opportunities.append(last_trade)

    if all_opportunities:
        log.info("=== Weekly Opportunities Report ===")
        for opp in all_opportunities:
            log.info(
                f"Stock: {opp.stock}, Entry: {opp.entry_price:.2f}, Confidence: {opp.confidence_score:.2f}"
            )
    else:
        log.info("No new opportunities found in the last 7 days.")
