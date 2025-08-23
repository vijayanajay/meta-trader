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

@app.command()
def test_data_service(
    stock: str = typer.Option("RELIANCE.NS", "--stock", "-s", help="Stock ticker."),
    start_date: str = typer.Option("2022-01-01", "--start", help="Start date."),
    end_date: str = typer.Option("2022-01-31", "--end", help="End date."),
) -> None:
    """
    Tests the DataService by fetching data for a stock.
    """
    from praxis_engine.services.data_service import DataService
    from praxis_engine.services.config_service import load_config

    print("Loading configuration...")
    config = load_config("config.ini")

    print(f"Initializing DataService with cache dir: {config.data.cache_dir}")
    data_service = DataService(cache_dir=config.data.cache_dir)

    sector_ticker = config.data.sector_map.get(stock)

    print(f"Fetching data for {stock}...")
    df = data_service.get_data(stock, start_date, end_date, sector_ticker)

    if df is not None:
        print(f"[bold green]Data fetched successfully![/bold green]")
        print(df.head())
    else:
        print(f"[bold red]Failed to fetch data for {stock}.[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
