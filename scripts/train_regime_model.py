# Add the project root to the python path to allow for absolute imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import typer
import pandas as pd
import numpy as np
import joblib
from rich import print
from sklearn.linear_model import LogisticRegression

from praxis_engine.core.models import Config
from praxis_engine.services.config_service import load_config
from praxis_engine.services.market_data_service import MarketDataService
from praxis_engine.core.features import calculate_market_features

app = typer.Typer()

# impure
def train_and_save_model(config: Config) -> bool:
    """
    Trains a market regime model and saves it to a file.

    Args:
        config: The application configuration object.

    Returns:
        True if the model was trained and saved successfully, False otherwise.
    """
    print("Initializing services...")
    market_data_service = MarketDataService(config.market_data.cache_dir)

    # Define and create model directory
    model_path = Path(config.regime_model.model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    print("Fetching market data for training...")
    tickers = [config.market_data.index_ticker, config.market_data.vix_ticker]
    market_data = market_data_service.get_market_data(
        tickers=tickers,
        start=config.market_data.training_start_date,
        end=config.data.end_date,
    )

    if not market_data or config.market_data.index_ticker not in market_data:
        print("[bold red]Failed to fetch Nifty data. Cannot train model.[/bold red]")
        return False

    print("Calculating features...")
    features_df = calculate_market_features(
        market_data=market_data,
        nifty_ticker=config.market_data.index_ticker,
        vix_ticker=config.market_data.vix_ticker,
    )

    # --- Define the Target Variable (y) ---
    # Heuristic: A "bad regime" (target=0) is when the 20-day forward volatility of Nifty is high.
    # A "good regime" (target=1) is when it's low. This aligns with the strategy's goal
    # of operating in low-volatility, mean-reverting environments.
    nifty_df = market_data[config.market_data.index_ticker]

    # Calculate forward-looking volatility
    forward_vol = (
        nifty_df["Close"].pct_change().rolling(window=20).std().shift(-20) * np.sqrt(252)
    )

    # Define high volatility threshold as the 75th percentile of historical volatility
    vol_threshold = forward_vol.quantile(config.regime_model.volatility_threshold_percentile)

    # Target: 1 for good regime (low future vol), 0 for bad regime (high future vol)
    target_series = (forward_vol < vol_threshold).astype(int)
    target = pd.DataFrame(target_series)
    target.columns = ["target"]

    # --- Prepare Data for Training ---
    full_df = features_df.join(target).dropna()

    if full_df.empty:
        print("[bold red]Not enough data to train the model after processing. Check date ranges and data quality.[/bold red]")
        return False

    feature_columns = [col for col in features_df.columns if col != "target"]
    X = full_df[feature_columns]
    y = full_df["target"]

    if len(y.unique()) < 2:
        print(f"[bold red]Not enough classes to train model. Only found class: {y.unique()}[/bold red]")
        return False

    print(f"Training model on {len(X)} samples...")
    print(f"Regime distribution:\n{y.value_counts(normalize=True)}")

    # --- Train and Save Model ---
    model = LogisticRegression(class_weight="balanced", random_state=42)
    model.fit(X, y)

    print(f"Saving model and feature columns to: {model_path}")
    joblib.dump({"model": model, "feature_columns": feature_columns}, model_path)

    print("[bold green]Model training complete and saved.[/bold green]")
    return True


@app.command()
def main(config_path: str = "config.ini"):
    """
    CLI entry point to train and save the market regime model.
    """
    print("Loading configuration...")
    config = load_config(config_path)

    # Add a simple check for the regime_model config section
    if not hasattr(config, 'regime_model'):
        print("[bold red]Missing [regime_model] section in config.ini[/bold red]")
        raise typer.Exit(code=1)

    success = train_and_save_model(config)
    if not success:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
