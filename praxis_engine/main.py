"""
Main CLI entry point for the Praxis Engine.
"""
import typer
from rich import print

from praxis_engine.services.config_service import load_config

app = typer.Typer(
    name="praxis-engine",
    help="A quantitative trading system for the Indian stock market.",
)

@app.command()
def verify_config(
    config_path: str = typer.Option(
        "praxis_engine/config.ini",
        "--config",
        "-c",
        help="Path to the configuration file.",
    )
) -> None:
    """
    Loads and verifies the configuration file.
    """
    print("Attempting to load configuration...")
    try:
        config = load_config(config_path)
        print("[bold green]Configuration loaded and validated successfully![/bold green]")
        print(config)
    except Exception as e:
        print(f"[bold red]Error loading configuration:[/bold red]")
        print(e)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
