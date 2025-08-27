import typer
from praxis_engine.core.logger import get_logger
from praxis_engine.services.config_service import ConfigService
from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Opportunity
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
    all_trades = []

    for stock in config.data.stocks_to_backtest:
        trades = orchestrator.run_backtest(
            stock=stock,
            start_date=config.data.start_date,
            end_date=config.data.end_date,
        )
        all_trades.extend(trades)

    report_generator = ReportGenerator()
    report = report_generator.generate_backtest_report(all_trades, config.data.start_date, config.data.end_date)
    logger.info(report)


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
    Generates a report based on the backtest results.
    """
    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()
    orchestrator = Orchestrator(config)
    opportunities: List[Opportunity] = []
    for stock in config.data.stocks:
        opportunity = orchestrator.generate_opportunities(stock)
        if opportunity:
            opportunities.append(opportunity)

    report_generator = ReportGenerator()
    report = report_generator.generate_opportunities_report(opportunities)
    logger.info(report)


if __name__ == "__main__":
    app()
