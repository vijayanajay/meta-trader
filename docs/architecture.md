# **"Praxis" Engine — System Architecture**

This document outlines the high-level architecture of the "Praxis" mean-reversion trading engine. The design prioritizes a clean separation of concerns, statelessness, and a data flow that ensures scientific rigor and reproducibility, adhering to the principles in `HARD_RULES.md`.

---

## 1. Core Principles

-   **Separation of Concerns:** The architecture strictly separates pure, offline-testable business logic (`core/`) from I/O-bound operations (`services/`).
-   **Statelessness:** All services are designed to be stateless. They are instantiated with a configuration and do not maintain state between method calls.
-   **Configuration Driven:** All operational parameters (thresholds, lookback periods, file paths, etc.) are managed in `config.ini` and loaded into a type-safe Pydantic `Config` object at runtime.
-   **CLI as Orchestrator:** The main application logic, including the orchestration of backtests and sensitivity analyses, is managed by the command-line interface (CLI) defined in `praxis_engine/main.py`. This keeps the core engine components focused on their specific tasks.

---

## 2. Component Diagram & Data Flow

The system follows a sequential pipeline for backtesting, orchestrated by the CLI.

```
[CLI: main.py] -> [Orchestrator]
      |
      |--- 1. [DataService] -> Fetches & Caches NSE Data
      |
      |--- 2. [Orchestrator] -> Pre-computes Indicators (Vectorized)
      |
      |--- 3. Loop (Walk-Forward):
      |      |
      |      |--- a. [SignalEngine] -> Generates Signal?
      |      |
      |      |--- b. [ValidationService] -> Applies Guards (Liquidity, Regime, Stat)
      |      |
      |      |--- c. [ExecutionSimulator] -> Simulates Trade & Calculates P/L
      |
      |--- 4. [ReportGenerator] -> Aggregates Trades & Generates MD Report
      |
      '--- 5. [main.py] -> Writes trade_log.csv
```

---

## 3. Directory & Module Structure (`praxis_engine/`)

The `praxis_engine` package is organized as follows:

-   `praxis_engine/`
    -   `main.py`: The CLI entry point using `Typer`. Orchestrates all high-level commands like `backtest` and `sensitivity-analysis`. Manages multiprocessing.
    -   `core/`: Contains the pure, central logic of the backtesting engine.
        -   `models.py`: Pydantic models for configuration (`Config`), data structures (`Trade`, `Opportunity`), and internal data transfer objects.
        -   `orchestrator.py`: The main walk-forward loop logic. Integrates all services to run a backtest for a single stock.
        -   `indicators.py`: Pure functions for calculating technical indicators (e.g., RSI, Bollinger Bands).
        -   `statistics.py`: Pure functions for statistical tests (e.g., Hurst Exponent, ADF).
        -   `logger.py`: Centralized logging configuration.
    -   `services/`: Contains modules that handle external interactions (I/O).
        -   `config_service.py`: Loads and validates the `config.ini` file into Pydantic models.
        -   `data_service.py`: Handles fetching data from `yfinance` and managing the local Parquet cache.
        -   `signal_engine.py`: Encapsulates the logic for identifying a preliminary trade signal based on indicator alignment.
        -   `validation_service.py`: Applies the guardrail logic (Liquidity, Regime, Stat) to a signal.
        -   `execution_simulator.py`: Simulates a trade, applying a realistic cost model (slippage, brokerage, STT).
        -   `report_generator.py`: Generates all user-facing Markdown reports from the backtest results.
        -   `llm_audit_service.py`: (If used) Handles communication with the external LLM API.
    -   `utils.py`: Contains small, stateless helper functions used across the codebase.

---

## 4. Key Architectural Decisions & Patterns

-   **Vectorized Pre-computation:** To avoid O(N^2) complexity, the `Orchestrator` pre-calculates all necessary indicators for the entire historical dataset in a single vectorized operation before starting the walk-forward loop. The loop then becomes a series of fast O(1) lookups.
-   **Parallelization via `multiprocessing`:** The `backtest` and `sensitivity-analysis` commands in `main.py` use a `multiprocessing.Pool` to parallelize the work across multiple CPU cores. Each stock is processed independently, making the problem "embarrassingly parallel."
-   **Trade Log as Ground Truth:** The backtester's primary output is the `results/trade_log.csv`. This machine-readable file contains a detailed record of every trade and is the foundational dataset for all subsequent analysis and reporting. The Markdown report is a human-readable summary of this data.
-   **Strict Separation of Concerns in Guards:** The `ValidationService` uses a modular "Guard" pattern. Each guard (`LiquidityGuard`, `RegimeGuard`, `StatGuard`) is a separate class responsible for a single validation check. This makes the validation logic easy to test, modify, and extend.
