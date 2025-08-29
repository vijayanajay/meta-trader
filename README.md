# Praxis Engine

The "Praxis" Engine is a quantitative trading system designed to identify and capitalize on high-probability mean-reversion opportunities within the Indian stock market (NSE).

The system's core philosophy is not to predict prices, but to apply a cascade of statistical and market-regime filters to isolate asymmetric risk-reward scenarios. It is built with a mindset of pragmatic minimalism, aiming for a small, robust, and deterministic codebase.

## Project Philosophy

This project adheres to a strict set of [30 hard rules](./docs/HARD_RULES.md) that emphasize:
- **Simplicity:** Prefer deletion over abstraction. Every line is a liability.
- **Determinism:** 100% type hints, strictly enforced. No global state.
- **Realism:** Backtesting includes costs, slippage, and liquidity checks.
- **Integrity:** The LLM is an auditor, not an originator. It never sees price data.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd praxis-engine
    ```

2.  **Install dependencies:**
    The project has a number of dependencies that need to be installed. You can install them using pip:
    ```bash
    pip install pandas yfinance statsmodels numpy pydantic python-dotenv openai typer pyarrow hurst pytest
    ```

3.  **Configure Environment:**
    Create a `.env` file by copying the example:
    ```bash
    cp .env.example .env
    ```
    You will need to add your OpenRouter API key to the `.env` file for the LLM audit functionality to work.

4.  **Configure the Strategy:**
    All strategy parameters, backtest settings, and filters are controlled by `config.ini`. You can modify this file to change:
    - The list of stocks to backtest (`stocks_to_backtest`).
    - The backtest date range (`start_date`, `end_date`).
    - The signal generation logic (`[signal_logic]` section).
    - Statistical filter thresholds (`[filters]` section).
    - Probabilistic scoring boundaries (`[scoring]` section).


## Usage

The primary entry point for the application is `run.py`, which uses Typer to provide a command-line interface.

### Available Commands

You can see a list of all available commands by running:
```bash
python run.py --help
```

### Run a Backtest

To run a backtest on the stocks defined in your `config.ini`, use the `backtest` command:
```bash
python run.py backtest
```
This will fetch the necessary data, run the walk-forward backtest for each stock, and print the results to the console.

## Project Structure

-   `praxis_engine/`: The main source code for the engine.
    -   `core/`: Core components like models, the orchestrator, and pure statistical/indicator functions.
    -   `services/`: Services that perform I/O operations, such as fetching data, interacting with the LLM, or simulating trades.
    -   `main.py`: The Typer-based CLI application definition.
-   `docs/`: Project documentation, including the PRD, architecture, and hard rules.
-   `tests/`: The pytest unit and integration test suite.
-   `config.ini`: The central configuration file for all strategy and system parameters.
-   `run.py`: The main script to execute the CLI application.
-   `.env.example`: An example environment file.
