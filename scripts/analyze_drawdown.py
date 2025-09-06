import pandas as pd
import typer
from pathlib import Path
from typing_extensions import Annotated
import sys

# Add the project root to the python path to allow importing from praxis_engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from praxis_engine.services.diagnostics_service import DiagnosticsService


app = typer.Typer()


@app.command()
def analyze(
    trade_log_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the trade_log.csv file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ]
):
    """
    Analyzes a trade log to identify drawdown periods and contributing factors.
    """
    try:
        trades_df = pd.read_csv(trade_log_path, parse_dates=["entry_date", "exit_date"])
    except FileNotFoundError:
        print(f"Error: Trade log file not found at {trade_log_path}")
        raise typer.Exit(code=1)

    if trades_df.empty:
        print("Trade log is empty. No analysis to perform.")
        raise typer.Exit()

    print("--- Analysis by Exit Reason ---")
    exit_reason_analysis = (
        trades_df.groupby("exit_reason")["net_return_pct"]
        .agg(["count", "sum", "mean"])
        .sort_values(by="sum")
    )
    print(exit_reason_analysis)
    print("-" * 30)

    drawdown_period = DiagnosticsService.analyze_drawdown(trades_df)

    if not drawdown_period:
        print("Could not determine drawdown period.")
        raise typer.Exit()


    print("\n--- Maximum Drawdown Period ---")
    print(f"Period started at peak on: {drawdown_period.start_date.date()}")
    print(f"Period ended at trough on: {drawdown_period.end_date.date()}")
    print(f"Maximum Drawdown: {drawdown_period.max_drawdown_pct:.2%}")
    print("-" * 30)

    # Filter for trades within the max drawdown period
    drawdown_trades = trades_df.loc[drawdown_period.trade_indices]

    print("\n--- Trades within Maximum Drawdown Period ---")
    if drawdown_trades.empty:
        print("No trades found within the maximum drawdown period.")
    else:
        # Display relevant columns for the drawdown trades
        display_cols = [
            "stock",
            "exit_date",
            "net_return_pct",
            "exit_reason",
            "holding_period_days",
        ]
        print(
            drawdown_trades[display_cols]
            .sort_values(by="exit_date")
            .to_string(index=False)
        )

        print("\n--- Drawdown Cohort Analysis ---")

        # 1. By Stock
        print("\n--- By Stock ---")
        stock_analysis = (
            drawdown_trades.groupby("stock")["net_return_pct"]
            .agg(["count", "sum", "mean"])
            .sort_values(by="sum")
        )
        print(stock_analysis)

        # 2. By Composite Score
        print("\n--- By Composite Score ---")
        score_bins = [0, 0.25, 0.5, 0.75, 1.0]
        drawdown_trades["score_bin"] = pd.cut(
            drawdown_trades["composite_score"], bins=score_bins
        )
        score_analysis = (
            drawdown_trades.groupby("score_bin", observed=False)["net_return_pct"]
            .agg(["count", "sum", "mean"])
            .sort_values(by="sum")
        )
        print(score_analysis)

        # 3. By Entry Sector Volatility
        print("\n--- By Entry Sector Volatility ---")
        vol_bins = [0, 15, 22, 100]
        drawdown_trades["vol_bin"] = pd.cut(
            drawdown_trades["entry_sector_vol"], bins=vol_bins
        )
        vol_analysis = (
            drawdown_trades.groupby("vol_bin", observed=False)["net_return_pct"]
            .agg(["count", "sum", "mean"])
            .sort_values(by="sum")
        )
        print(vol_analysis)


if __name__ == "__main__":
    app()
