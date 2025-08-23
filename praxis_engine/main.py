"""
Main CLI entry point for the Praxis Engine.
"""
import typer
from dotenv import load_dotenv

from praxis_engine.services.config_service import load_config
from praxis_engine.core.logger import get_logger

# Load environment variables from .env file
load_dotenv()

log = get_logger(__name__)

app = typer.Typer(
    name="praxis-engine",
    help="A quantitative trading system for the Indian stock market.",
    pretty_exceptions_show_locals=False,
)

@app.command()
def verify_config(
    config_path: str = typer.Option("config.ini", "--config", "-c", help="Path to config.")
) -> None:
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


@app.command()
def backtest(
    config_path: str = typer.Option("config.ini", "--config", "-c", help="Path to config."),
) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    from praxis_engine.core.orchestrator import Orchestrator

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
        for trade in all_trades:
            log.info(trade)
    else:
        log.info("Backtest complete. No trades were executed.")


if __name__ == "__main__":
    app()
