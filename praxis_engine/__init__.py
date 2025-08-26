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
    Runs the engine on the latest data to find new opportunities and saves a report.
    """
    from praxis_engine.core.orchestrator import Orchestrator
    from praxis_engine.services.report_generator import ReportGenerator

    log.info("Loading configuration...")
    config = load_config(config_path)

    orchestrator = Orchestrator(config)
    report_generator = ReportGenerator()

    opportunities = []
    for stock in config.data.stocks_to_backtest:
        # Use a lookback that's long enough for indicators but not excessive.
        opportunity = orchestrator.generate_opportunities(stock, lookback_days=365)
        if opportunity:
            opportunities.append(opportunity)

    report = report_generator.generate_opportunities_report(opportunities)

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / f"opportunities_{datetime.date.today()}.md"

    with open(report_path, "w") as f:
        f.write(report)

    log.info(f"Opportunities report saved to {report_path}")
    log.info("\n" + report)
