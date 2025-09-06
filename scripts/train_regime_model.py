# Add the project root to the python path to allow for absolute imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import typer
from rich import print

from praxis_engine.services.config_service import load_config
from praxis_engine.services.market_data_service import MarketDataService
from praxis_engine.core.features import calculate_market_features

app = typer.Typer()

@app.command()
def main(config_path: str = "config.ini"):
    """
    Trains and saves the market regime model.
    This is currently a stub that demonstrates feature calculation.
    """
    print("Loading configuration...")
    config = load_config(config_path)

    print("Initializing services...")
    market_data_service = MarketDataService(config.market_data.cache_dir)

    print("Fetching market data...")
    tickers = [config.market_data.index_ticker, config.market_data.vix_ticker]
    market_data = market_data_service.get_market_data(
        tickers=tickers,
        start=config.market_data.training_start_date,
        end=config.data.end_date,
    )

    if not market_data or config.market_data.index_ticker not in market_data or config.market_data.vix_ticker not in market_data:
        print("[bold red]Failed to fetch all required market data. Exiting.[/bold red]")
        raise typer.Exit(code=1)

    print("Calculating features...")
    features_df = calculate_market_features(
        market_data=market_data,
        nifty_ticker=config.market_data.index_ticker,
        vix_ticker=config.market_data.vix_ticker,
    )

    print("\n[bold green]Feature calculation complete.[/bold green]")
    print("Displaying head of features DataFrame:")
    print(features_df.head())
    print("\nDisplaying tail of features DataFrame:")
    print(features_df.tail())

    print("\n[bold yellow]NOTE: This is a stub script. Model training is not yet implemented.[/bold yellow]")


if __name__ == "__main__":
    app()
