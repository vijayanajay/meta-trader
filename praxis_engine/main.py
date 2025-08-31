import typer
from pathlib import Path
import datetime
import sys
from dotenv import load_dotenv
from tqdm import tqdm

from praxis_engine.core.logger import get_logger, setup_file_logger
from praxis_engine.services.config_service import ConfigService
from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import BacktestMetrics, Config, Opportunity, Trade, RunMetadata
from praxis_engine.services.report_generator import ReportGenerator
from praxis_engine.utils import get_git_commit_hash
from typing import List, Dict

# Load environment variables from .env file
load_dotenv()

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
) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    setup_file_logger()
    logger.info("File logging configured. Starting backtest...")

    config_service = ConfigService(config_path)
    config: Config = config_service.load_config()
    orchestrator = Orchestrator(config)
    all_trades: List[Trade] = []
    per_stock_trades: Dict[str, List[Trade]] = {}
    aggregated_metrics = BacktestMetrics()
    per_stock_metrics: Dict[str, BacktestMetrics] = {}
    report_generator = ReportGenerator()

    # --- Metadata Collection ---
    run_metadata = RunMetadata(
        run_timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        config_path=config_path,
        git_commit_hash=get_git_commit_hash(),
    )
    logger.info(f"Git commit hash: {run_metadata.git_commit_hash}")
    # -------------------------

    stock_list = config.data.stocks_to_backtest
    with tqdm(total=len(stock_list), desc="Backtesting Stocks", file=sys.stderr) as pbar:
        for stock in stock_list:
            pbar.set_description(f"Processing {stock}")
            result = orchestrator.run_backtest(
                stock=stock,
                start_date=config.data.start_date,
                end_date=config.data.end_date,
            )
            per_stock_trades[stock] = result["trades"]
            per_stock_metrics[stock] = result["metrics"]
            all_trades.extend(result["trades"])
            metrics = result["metrics"]
            # Aggregate metrics
            aggregated_metrics.potential_signals += metrics.potential_signals
            aggregated_metrics.rejections_by_llm += metrics.rejections_by_llm
            aggregated_metrics.trades_executed += metrics.trades_executed
            for guard, count in metrics.rejections_by_guard.items():
                aggregated_metrics.rejections_by_guard[guard] = aggregated_metrics.rejections_by_guard.get(guard, 0) + count


            pbar.update(1)

    if not all_trades:
        logger.info("Backtest complete. No trades were executed.")
        return

    logger.info("\n========== Overall Backtest Summary ==========")
    logger.debug(f"Aggregated metrics for report: {aggregated_metrics}")
    final_report = report_generator.generate_backtest_report(
        trades=all_trades,
        metrics=aggregated_metrics,
        start_date=config.data.start_date,
        end_date=config.data.end_date,
        metadata=run_metadata,
    )

    per_stock_report = report_generator.generate_per_stock_report(
        per_stock_metrics=per_stock_metrics,
        per_stock_trades=per_stock_trades,
    )

    final_report += "\n" + per_stock_report
    logger.debug(f"Final report string to be written:\n{final_report}")

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "backtest_summary.md"
    report_path.write_text(final_report, encoding='utf-8')

    logger.info(f"Overall backtest report saved to {report_path}")
    logger.info(final_report)
    logger.info("==============================================")


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
    setup_file_logger()
    logger.info("File logging configured. Generating opportunities report...")

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
    report_path.write_text(report, encoding='utf-8')

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
    setup_file_logger()
    logger.info("File logging configured. Starting sensitivity analysis...")

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
    report_path.write_text(report, encoding='utf-8')

    logger.info(f"Sensitivity analysis report saved to {report_path}")
    logger.info("\n" + report)


if __name__ == "__main__":
    app()
