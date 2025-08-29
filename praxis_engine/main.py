import typer
from pathlib import Path
import datetime
from dotenv import load_dotenv

import pandas as pd
from tqdm import tqdm

from praxis_engine.core.logger import get_logger
from praxis_engine.services.config_service import ConfigService
from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import Config, Opportunity, Trade
from praxis_engine.services.report_generator import ReportGenerator
from typing import List

# Load environment variables from .env file
load_dotenv()

# Initialize Typer app
app = typer.Typer()
logger = get_logger(__name__)


def _calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculates the Sharpe ratio for a series of returns."""
    if returns.empty or returns.std() == 0:
        return 0.0
    # Annualize the Sharpe ratio
    return (returns.mean() - risk_free_rate) / returns.std() * (252 ** 0.5)


@app.command()
def backtest(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()
    orchestrator = Orchestrator(config)
    all_trades: List[Trade] = []

    logger.summary("Starting backtest...")

    stocks_to_backtest = config.data.stocks_to_backtest
    with tqdm(total=len(stocks_to_backtest), desc="Backtesting Stocks") as pbar:
        for stock in stocks_to_backtest:
            pbar.set_description(f"Backtesting {stock}")
            trades = orchestrator.run_backtest(
                stock=stock,
                start_date=config.data.start_date,
                end_date=config.data.end_date,
            )
            if trades:
                all_trades.extend(trades)
                returns = pd.Series([t.net_return_pct for t in trades])
                win_rate = (returns > 0).mean() * 100
                sharpe = _calculate_sharpe_ratio(returns)
                logger.summary(
                    f"  {stock}: {len(trades)} trades, Win Rate: {win_rate:.2f}%, Sharpe: {sharpe:.2f}"
                )
            else:
                logger.summary(f"  {stock}: No trades executed.")
            pbar.update(1)

    if not all_trades:
        logger.summary("\nBacktest complete. No trades were executed across all stocks.")
        return

    logger.summary("\n" + "=" * 50)
    logger.summary("Overall Backtest Summary")
    logger.summary("=" * 50)

    report_generator = ReportGenerator()
    report = report_generator.generate_backtest_report(
        all_trades, config.data.start_date, config.data.end_date
    )

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "backtest_summary.md"
    report_path.write_text(report)

    logger.summary(f"\nDetailed backtest report saved to {report_path}")
    logger.summary("See `results/backtest_results.log` for detailed trade-by-trade logs.")
    logger.summary("\n" + report)


@app.command()
def generate_report(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
) -> None:
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


@app.command()
def sensitivity_analysis(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
) -> None:
    """
    Runs a sensitivity analysis for a parameter defined in the config file.
    """
    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()

    if not config.sensitivity_analysis:
        logger.error("`sensitivity_analysis` section not found in the config file.")
        raise typer.Exit(code=1)

    orchestrator = Orchestrator(config)
    results = orchestrator.run_sensitivity_analysis()

    if not results:
        logger.info("Sensitivity analysis complete. No results to report.")
        return

    logger.info("Sensitivity analysis complete. Generating report...")
    report_generator = ReportGenerator()
    report = report_generator.generate_sensitivity_report(
        results, config.sensitivity_analysis.parameter_to_vary
    )

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "sensitivity_analysis_report.md"
    report_path.write_text(report)

    logger.info(f"Sensitivity analysis report saved to {report_path}")
    logger.info("\n" + report)


if __name__ == "__main__":
    app()
