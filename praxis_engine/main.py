import typer
from pathlib import Path
import datetime

from praxis_engine.core.logger import get_logger
from praxis_engine.services.config_service import ConfigService
from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Opportunity, Trade
from praxis_engine.services.report_generator import ReportGenerator
from typing import List

# Initialize Typer app
app = typer.Typer()
logger = get_logger(__name__)


@app.command()
def backtest(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
):
    """
    Runs a backtest for stocks defined in the config file.
    """
    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()
    orchestrator = Orchestrator(config)
    all_trades: List[Trade] = []

    for stock in config.data.stocks_to_backtest:
        trades = orchestrator.run_backtest(
            stock=stock,
            start_date=config.data.start_date,
            end_date=config.data.end_date,
        )
        all_trades.extend(trades)

    if not all_trades:
        logger.info("Backtest complete. No trades were executed.")
        return

    logger.info(f"Backtest complete. Total trades executed: {len(all_trades)}")
    report_generator = ReportGenerator()
    report = report_generator.generate_backtest_report(
        all_trades, config.data.start_date, config.data.end_date
    )

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "backtest_summary.md"
    report_path.write_text(report)

    logger.info(f"Backtest report saved to {report_path}")
    logger.info("\n" + report)


@app.command()
def generate_report(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
):
    """
    Generates a report of new opportunities based on the latest data.
    """
    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()
    orchestrator = Orchestrator(config)
    opportunities: List[Opportunity] = []
    for stock in config.data.stocks_to_backtest:
        opportunity = orchestrator.generate_opportunities(stock)
        if opportunity:
            opportunities.append(opportunity)

    report_generator = ReportGenerator()
    report = report_generator.generate_opportunities_report(opportunities)

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / f"opportunities_{datetime.date.today()}.md"
    report_path.write_text(report)

    logger.info(f"Opportunities report saved to {report_path}")
    logger.info("\n" + report)


if __name__ == "__main__":
    app()
