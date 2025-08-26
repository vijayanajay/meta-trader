#!/usr/bin/env python
"""
Main CLI entry point for the Praxis Engine.
"""
import typer
from dotenv import load_dotenv

from praxis_engine import main

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="praxis-engine",
    help="A quantitative trading system for the Indian stock market.",
    pretty_exceptions_show_locals=False,
)

@app.command()
def verify_config(
    config_path: str = typer.Option(
        "config.ini", "--config", "-c", help="Path to config."
    )
) -> None:
    """
    Loads and verifies the configuration file.
    """
    main.verify_config(config_path)

@app.command()
def backtest(
    config_path: str = typer.Option(
        "config.ini", "--config", "-c", help="Path to config."
    )
) -> None:
    """
    Runs a backtest for stocks defined in the config file.
    """
    main.backtest(config_path)

@app.command()
def generate_report(
    config_path: str = typer.Option(
        "config.ini", "--config", "-c", help="Path to config."
    )
) -> None:
    """
    Runs the engine on the latest data to find new opportunities.
    """
    main.generate_report(config_path)

if __name__ == "__main__":
    app()
