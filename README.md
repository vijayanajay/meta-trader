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
    This project uses Poetry for dependency management. It is recommended to install the dependencies in a virtual environment.
    ```bash
    pip install poetry
    poetry install
    ```
    Alternatively, for a quick start, you can install the project in editable mode with pip:
    ```bash
    pip install -e .
    ```

3.  **Configure Environment:**
    Create a `.env` file by copying the example:
    ```bash
    cp .env.example .env
    ```
    You do not need to modify this file to get started, as it is pre-configured to use the free tier of the OpenRouter API.

4.  **Configure the Strategy:**
    All strategy parameters, backtest settings, and filters are controlled by `config.ini`. You can modify this file to change:
    - The list of stocks to backtest (`stocks_to_backtest`).
    - The backtest date range (`start_date`, `end_date`).
    - The signal generation logic (`[signal_logic]` section).
    - Statistical filter thresholds (`[filters]` section).


## Usage

The primary entry point for the application is the `praxis` command-line interface.

### Verify Configuration

To load and validate your `config.ini` file, run:
```bash
praxis verify-config
```

### Run a Backtest

To run a backtest on the stocks defined in your `config.ini`, use the `backtest` command:
```bash
praxis backtest
```
This will fetch the necessary data, run the walk-forward backtest for each stock, and print the results of any simulated trades to the console.

Alternatively, you can use the provided runner script:
```bash
python run.py
```

## Project Structure

-   `praxis_engine/`: The main source code for the engine.
    -   `core/`: Core components like models, the orchestrator, and pure statistical/indicator functions.
    -   `services/`: Services that perform I/O operations, such as fetching data, interacting with the LLM, or simulating trades.
    -   `main.py`: The Typer-based CLI application entry point.
-   `docs/`: Project documentation, including the PRD, architecture, and hard rules.
-   `tests/`: The pytest unit and integration test suite.
-   `config.ini`: The central configuration file for all strategy and system parameters.
-   `run.py`: A simple script to execute a default backtest run.
