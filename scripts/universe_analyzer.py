# --- IMPORTS ---
import logging
import warnings
from pathlib import Path
import pandas as pd
import sys

# Ensure the package is in the path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from praxis_engine.core.statistics import hurst_exponent
from praxis_engine.services.data_service import DataService
from praxis_engine.services.config_service import ConfigService
from praxis_engine.core.logger import setup_file_logger

# --- SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
# Use the file logger setup from the core library
setup_file_logger(file_name="universe_analyzer.log")
log = logging.getLogger(__name__)

# --- CONSTANTS ---
# Using a smaller, representative list for this script as per task description.
# A full Nifty 500 list would be read from a file in a production scenario.
NIFTY_500_SUBSET = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", "HINDUNILVR.NS", "ITC.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "ADANIENT.NS", "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "TATAMOTORS.NS",
    "NTPC.NS", "AXISBANK.NS", "DMART.NS", "ADANIGREEN.NS", "ADANIPORTS.NS",
    "ULTRACEMCO.NS", "ASIANPAINT.NS", "COALINDIA.NS", "BAJAJFINSV.NS",
    "POWERGRID.NS", "WIPRO.NS", "NESTLEIND.NS", "M&M.NS", "IOC.NS",
    "DLF.NS", "SBILIFE.NS", "GRASIM.NS", "HDFCLIFE.NS", "PIDILITIND.NS",
    "BAJAJ-AUTO.NS", "INDUSINDBK.NS", "JSWSTEEL.NS", "CIPLA.NS", "VEDL.NS",
    "ADANIPOWER.NS", "EICHERMOT.NS", "DRREDDY.NS", "TATASTEEL.NS", "HEROMOTOCO.NS"
]

OUT_OF_SAMPLE_START = "2010-01-01"
OUT_OF_SAMPLE_END = "2017-12-31"
HURST_THRESHOLD = 0.5

# --- SCRIPT LOGIC ---

# impure
def analyze_universe(tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Analyzes a universe of stocks to find mean-reverting candidates.

    Args:
        tickers: A list of stock tickers to analyze.
        start_date: The start date for the analysis period.
        end_date: The end date for the analysis period.

    Returns:
        A pandas DataFrame with tickers and their Hurst exponents,
        sorted by the Hurst exponent.
    """
    log.info(f"Starting universe analysis for {len(tickers)} stocks...")
    log.info(f"Analysis period: {start_date} to {end_date}")

    config_service = ConfigService(path="config.ini")
    config = config_service.load_config()
    data_service = DataService(cache_dir=config.data.cache_dir)

    results = []

    for ticker in tickers:
        try:
            log.debug(f"Fetching data for {ticker}...")
            stock_data = data_service.get_data(ticker, start_date, end_date)

            if stock_data is None or stock_data.empty:
                log.warning(f"No data found for {ticker}. Skipping.")
                continue

            # Ensure there's enough data to calculate Hurst
            if len(stock_data) < 100:
                log.warning(f"Not enough data for {ticker} (len: {len(stock_data)}). Skipping.")
                continue

            h = hurst_exponent(stock_data["Close"])
            log.debug(f"Hurst exponent for {ticker}: {h:.4f}")
            results.append({"ticker": ticker, "hurst": h})

        except Exception as e:
            log.error(f"Failed to process {ticker}. Error: {e}", exc_info=False)

    log.info("Analysis complete. Compiling results...")
    return pd.DataFrame(results).sort_values(by="hurst", ascending=True)


def main() -> None:
    """Main function to run the universe analysis."""
    # impure
    results_df = analyze_universe(
        tickers=NIFTY_500_SUBSET,
        start_date=OUT_OF_SAMPLE_START,
        end_date=OUT_OF_SAMPLE_END,
    )

    mean_reverting_stocks = results_df[results_df["hurst"] < HURST_THRESHOLD]

    print("\n--- Universe Analysis Results ---")
    print(f"Found {len(mean_reverting_stocks)} potential mean-reverting stocks (Hurst < {HURST_THRESHOLD}):")
    print("-" * 35)

    # Print a copy-paste ready list for config.ini
    stock_list_str = ", ".join(mean_reverting_stocks["ticker"].tolist())
    print("\n[COPY-PASTE FOR CONFIG.INI]")
    print(f"stocks_to_backtest = {stock_list_str}\n")


if __name__ == "__main__":
    main()
