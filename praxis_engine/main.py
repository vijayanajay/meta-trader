import typer
from pathlib import Path
import datetime
import sys
from dotenv import load_dotenv
from tqdm import tqdm
import multiprocessing
from itertools import repeat

from praxis_engine.core.logger import get_logger, setup_file_logger
from praxis_engine.services.config_service import load_config
from praxis_engine.core.orchestrator import Orchestrator
from praxis_engine.core.models import BacktestMetrics, Config, Opportunity, Trade, RunMetadata
from praxis_engine.services.report_generator import ReportGenerator
from praxis_engine.utils import get_git_commit_hash
from typing import List, Dict, Tuple, Optional, Any
import os

# Load environment variables from .env file
load_dotenv()

# Initialize Typer app
app = typer.Typer()
logger = get_logger(__name__)


def run_backtest_for_stock(payload: Tuple[str, str]) -> Dict[str, Any]:
    """
    Top-level helper function to run a backtest for a single stock.
    Designed to be picklable for multiprocessing.
    Returns trade data as a list of dicts for performance.
    """
    stock, config_path = payload
    config: Config = load_config(config_path)
    orchestrator = Orchestrator(config)

    result = orchestrator.run_backtest(
        stock=stock,
        start_date=config.data.start_date,
        end_date=config.data.end_date,
    )
    # Convert Trade objects to dicts for faster pickling
    result["trades"] = [trade.model_dump() for trade in result["trades"]]
    result["stock"] = stock
    return result


def determine_process_count(stock_list: List[str], cfg_workers: Optional[int]) -> int:
    """
    Determine number of worker processes to use given the stock list and
    optional workers specified in config.

    Returns an int >= 1.
    """
    cpu_cores = multiprocessing.cpu_count()
    if cfg_workers is None:
        return min(len(stock_list) or 1, cpu_cores)
    return max(1, int(cfg_workers))


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

    config: Config = load_config(config_path)
    all_trades_dicts: List[Dict] = []
    per_stock_trades: Dict[str, List[Dict]] = {}
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
    payloads = zip(stock_list, repeat(config_path))

    # Determine number of worker processes from config
    cfg_workers = getattr(config.data, "workers", None)
    processes = determine_process_count(stock_list, cfg_workers)
    logger.info(
        f"Using {processes} worker process(es) (config.workers: {cfg_workers}, cpu_cores: {multiprocessing.cpu_count()})"
    )

    with multiprocessing.Pool(processes=processes) as pool:
        with tqdm(
            total=len(stock_list), desc="Backtesting Stocks", file=sys.stderr
        ) as pbar:
            for result in pool.imap_unordered(run_backtest_for_stock, payloads):
                stock = result.pop("stock")
                pbar.set_description(f"Processing {stock}")

                per_stock_trades[stock] = result["trades"]
                per_stock_metrics[stock] = result["metrics"]
                all_trades_dicts.extend(result["trades"])
                metrics = result["metrics"]
                # Aggregate metrics
                aggregated_metrics.potential_signals += metrics.potential_signals
                aggregated_metrics.rejections_by_llm += metrics.rejections_by_llm
                aggregated_metrics.trades_executed += metrics.trades_executed
                for guard, count in metrics.rejections_by_guard.items():
                    aggregated_metrics.rejections_by_guard[guard] = (
                        aggregated_metrics.rejections_by_guard.get(guard, 0) + count
                    )
                pbar.update(1)

    if not all_trades_dicts:
        logger.info("Backtest complete. No trades were executed.")
        return

    # --- Create and export the master trade log DataFrame ---
    import pandas as pd

    trade_df = pd.DataFrame(all_trades_dicts)

    # Reorder columns to match the specification in tasks.md for the trade_log.csv
    trade_log_columns = [
        "stock", "entry_date", "exit_date", "holding_period_days", "entry_price",
        "exit_price", "net_return_pct", "exit_reason", "composite_score",
        "liquidity_score", "regime_score", "stat_score", "entry_hurst",
        "entry_adf_p_value", "entry_sector_vol", "config_bb_length",
        "config_rsi_length", "config_atr_multiplier"
    ]
    # Ensure all specified columns exist, fill missing with None or NaN
    for col in trade_log_columns:
        if col not in trade_df.columns:
            trade_df[col] = np.nan
    trade_df = trade_df[trade_log_columns]


    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    trade_log_path = results_dir / "trade_log.csv"
    trade_df.to_csv(trade_log_path, index=False, encoding='utf-8')
    logger.info(f"Trade log saved to {trade_log_path}")
    # ---------------------------------------------------------

    logger.info("\n========== Overall Backtest Summary ==========")
    logger.debug(f"Aggregated metrics for report: {aggregated_metrics}")
    final_report = report_generator.generate_backtest_report(
        trades_df=trade_df,
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

    config: Config = load_config(config_path)
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


import numpy as np
import copy
from praxis_engine.core.models import BacktestSummary
from praxis_engine.utils import get_nested_attr, set_nested_attr


def _aggregate_trades(trades: List[Trade], param_value: float) -> BacktestSummary:
    """
    Aggregates a list of trades into a BacktestSummary object.
    """
    if not trades:
        return BacktestSummary(
            parameter_value=param_value,
            total_trades=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            net_return_pct_mean=0.0,
            net_return_pct_std=0.0
        )

    returns = [t.net_return_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(trades) if trades else 0.0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999.0

    return BacktestSummary(
        parameter_value=param_value,
        total_trades=len(trades),
        win_rate_pct=win_rate * 100,
        profit_factor=profit_factor,
        net_return_pct_mean=float(np.mean(returns)) * 100,
        net_return_pct_std=float(np.std(returns)) * 100
    )


def run_backtest_for_stock_with_config(payload: Tuple[str, Config]) -> Dict[str, Any]:
    """
    Top-level helper function to run a backtest for a single stock with a given config.
    Designed to be picklable for multiprocessing.
    """
    stock, config = payload
    orchestrator = Orchestrator(config)

    result = orchestrator.run_backtest(
        stock=stock,
        start_date=config.data.start_date,
        end_date=config.data.end_date,
    )
    result["stock"] = stock
    return result


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

    base_config: Config = load_config(config_path)

    if not base_config.sensitivity_analysis:
        logger.error("`sensitivity_analysis` section not found in the config file.")
        raise typer.Exit(code=1)

    sa_config = base_config.sensitivity_analysis
    param_name = sa_config.parameter_to_vary
    start = sa_config.start_value
    end = sa_config.end_value
    step = sa_config.step_size

    logger.info(f"Starting sensitivity analysis for '{param_name}' from {start} to {end} with step {step}")

    results: List[BacktestSummary] = []
    stock_list = base_config.data.stocks_to_backtest

    for value_np in np.arange(start, end + step, step):
        value = float(value_np)
        logger.info(f"Running backtest with {param_name} = {value:.4f}")

        run_config = copy.deepcopy(base_config)

        final_value: float | int = value
        if param_name in ['strategy_params.bb_length', 'strategy_params.rsi_length',
                        'strategy_params.hurst_length', 'strategy_params.exit_days',
                        'strategy_params.min_history_days', 'strategy_params.liquidity_lookback_days',
                        'exit_logic.atr_period', 'exit_logic.max_holding_days']:
            final_value = int(value)

        set_nested_attr(run_config, param_name, final_value)

        all_trades: List[Trade] = []
        payloads = zip(stock_list, repeat(run_config))

        cfg_workers = getattr(base_config.data, "workers", None)
        processes = determine_process_count(stock_list, cfg_workers)

        with multiprocessing.Pool(processes=processes) as pool:
            desc = f"Analyzing {param_name}={value:.2f}"
            with tqdm(total=len(stock_list), desc=desc, file=sys.stderr) as pbar:
                for result in pool.imap_unordered(run_backtest_for_stock_with_config, payloads):
                    all_trades.extend(result["trades"])
                    pbar.update(1)

        summary = _aggregate_trades(all_trades, value)
        results.append(summary)
        logger.info(f"Summary for {param_name} = {value:.4f}: {summary.total_trades} trades")

    if not results:
        logger.info("Sensitivity analysis complete. No results to report.")
        return

    logger.info("Sensitivity analysis complete. Generating report...")
    report_generator = ReportGenerator()
    report = report_generator.generate_sensitivity_report(
        results, base_config.sensitivity_analysis.parameter_to_vary
    )

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    report_path = results_dir / "sensitivity_analysis_report.md"
    report_path.write_text(report, encoding='utf-8')

    logger.info(f"Sensitivity analysis report saved to {report_path}")
    logger.info("\n" + report)


if __name__ == "__main__":
    app()
