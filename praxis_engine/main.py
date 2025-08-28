import typer
from pathlib import Path
import datetime
from dotenv import load_dotenv

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

# We will initialize the logger inside each command to pass the debug flag.
logger = get_logger(__name__)


from praxis_engine.core.exceptions import LLMConnectionError

@app.command()
def backtest(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging on the console.",
    ),
) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    global logger
    logger = get_logger(__name__, debug=debug)
    try:
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

        # Log LLM stats after the run
        llm_stats = (
            f"LLM Audit Stats: "
            f"{orchestrator.llm_audit_service.successful_calls} successful, "
            f"{orchestrator.llm_audit_service.failed_calls} failed."
        )
        logger.info(llm_stats)

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

    except LLMConnectionError as e:
        logger.error(f"A critical LLM error occurred: {e}")
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.command()
def generate_report(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging on the console.",
    ),
) -> None:
    """
    Generates a report of new opportunities based on the latest data.
    """
    global logger
    logger = get_logger(__name__, debug=debug)
    try:
        config_service = ConfigService(config_path)
        config: Config = config_service.load_config()
        orchestrator = Orchestrator(config)
        opportunities: List[Opportunity] = []
        for stock in config.data.stocks_to_backtest:
            opportunity = orchestrator.generate_opportunities(stock)
            if opportunity:
                opportunities.append(opportunity)

        # Log LLM stats after the run
        llm_stats = (
            f"LLM Audit Stats: "
            f"{orchestrator.llm_audit_service.successful_calls} successful, "
            f"{orcheator.llm_audit_service.failed_calls} failed."
        )
        logger.info(llm_stats)

        report_generator = ReportGenerator()
        report = report_generator.generate_opportunities_report(opportunities)

        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        report_path = results_dir / f"opportunities_{datetime.date.today()}.md"
        report_path.write_text(report)

        logger.info(f"Opportunities report saved to {report_path}")
        logger.info("\n" + report)
    except LLMConnectionError as e:
        logger.error(f"A critical LLM error occurred: {e}")
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.command()
def sensitivity_analysis(
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging on the console.",
    ),
) -> None:
    """
    Runs a sensitivity analysis for a parameter defined in the config file.
    """
    global logger
    logger = get_logger(__name__, debug=debug)
    try:
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
    except LLMConnectionError as e:
        logger.error(f"A critical LLM error occurred: {e}")
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
