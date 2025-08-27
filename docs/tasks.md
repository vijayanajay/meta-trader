Of course. Here is a comprehensive and detailed task breakdown for implementing the "Praxis" engine, written with the specified mindset of Kailash Nadh and ensuring no detail from the PRD, project brief, or architecture is missed.

---

# **"Praxis" Engine — Task Breakdown**

This document provides a detailed, sequential list of tasks required to build the "Praxis" Mean-Reversion Engine. Each task is designed as a small, logical unit of work, mapping directly to the requirements in the `prd.md` and `architecture.md`. We build methodically, test rigorously, and earn complexity. We do not build for a hypothetical future.

## Epic 1: Bedrock - The Data & Statistical Foundation

*Goal: To establish a reliable, reproducible data pipeline and the core statistical tools. Without a rock-solid foundation of clean, correct data and validated mathematical functions, the entire system is worthless. This epic builds the non-negotiable prerequisites.*

---

### Task 1 — Project Scaffolding & Configuration

*   **Rationale:** A project's long-term viability is decided in the first hour. We will establish a clean, reproducible structure and a centralized, type-safe configuration system from the outset. No shortcuts.
*   **Items to implement:**
    *   Create the full directory structure as defined in `architecture.md` (`praxis_engine/`, `core/`, `services/`, `prompts/`, etc.).
    *   Initialize a Git repository with a `.gitignore` that excludes `data_cache/`, `results/`, `__pycache__/`, and `.env`.
    *   Create `pyproject.toml` to define the project and configure `mypy` for strict type checking.
    *   Create `config.ini` with sections for `[data]`, `[strategy_params]`, `[filters]`, and `[llm]`. Populate with all thresholds from the PRD (e.g., `sector_vol_threshold = 22.0`, `liquidity_turnover_crores = 5.0`).
    *   Implement `services/config_service.py` to load and parse `config.ini`.
    *   Implement `core/models.py` with a Pydantic `Config` model that provides type-safe access to all configuration values.
    *   Create the CLI entry point `main.py` using `Typer` with a placeholder command that loads the config and prints it.
*   **Status:** Complete

---
### Task 1.1 — Fix Typer CLI Invocation

*   **Rationale:** The Typer CLI is not working as expected. This needs to be fixed to ensure the CLI is usable.
*   **Items to implement:**
    *   Investigate the `Typer` invocation issue mentioned in `docs/memory.md`.
    *   Fix the issue and ensure that `python -m praxis_engine.main verify-config` works as expected.
*   **Status:** Complete. **Resolution**: The CLI invocation was fixed by establishing a robust poetry script entry point (`poetry run praxis`) and moving all business logic out of `praxis_engine/__init__.py` into a dedicated `cli.py` module. The `run.py` script was deprecated in favor of this standard mechanism.

---

### Task 2 — Data Service for Indian Markets

*   **Rationale:** Data is the lifeblood. This service must be robust, efficient, and acutely aware of Indian market specifics. We will use the correct data sources and implement caching to make research fast and reproducible.
*   **Items to implement:**
    *   Add `yfinance` and `pyarrow` to `pyproject.toml`.
    *   Implement `services/data_service.py` with a `DataService` class.
    *   The `get_data(stock, start_date, end_date)` method must:
        1.  Construct a cache filename (e.g., `HDFCBANK_2010-01-01_2023-12-31.parquet`).
        2.  If the cache file exists, load and return the DataFrame from it.
        3.  If not, fetch equity data using `yfinance.download`.
        4.  Fetch the corresponding Nifty sector index data using `yfinance`.
        5.  Calculate the 20-day rolling annualized `sector_vol` and merge it into the main DataFrame.
        6.  Perform basic cleaning and save the final, clean DataFrame to the Parquet cache file.
*   **Status:** Complete

---

### Task 3 — Core Statistical & Indicator Library

*   **Rationale:** To create a library of pure, well-tested functions for all required statistical tests and technical indicators. These are the mathematical building blocks of our strategy and must be provably correct.
*   **Items to implement:**
    *   Create `core/indicators.py` for technical indicators. Implement functions for:
        *   Bollinger Bands (`bbands(series, length, std)`)
        *   Relative Strength Index (`rsi(series, length)`)
    *   Create `core/statistics.py` for statistical tests. Implement functions for:
        *   Augmented Dickey-Fuller test (`adf_test(series)`) which returns the p-value.
        *   Hurst Exponent (`hurst_exponent(series)`) which returns the H value.
*   **Status:** Complete

---

## Epic 2: The Filtering Cascade - Signal & Validation

*Goal: To codify the core logic of the system. This involves translating the multi-frame signal generation rules and the non-negotiable statistical and contextual guardrails into deterministic code. This is where the "edge" is built.*

---

### Task 4 — Multi-Frame Signal Engine

*   **Rationale:** A simple BB+RSI signal is noise. The PRD specifies that the edge comes from multi-frame alignment. This engine will implement that precise logic to generate preliminary signals.
*   **Items to implement:**
    *   In `core/models.py`, define a Pydantic `Signal` model to hold entry price, stop-loss, and other relevant signal data.
    *   Implement `services/signal_engine.py` with a `SignalEngine` class.
    *   The `generate_signal(df_daily)` method must implement the exact multi-frame alignment check from the PRD.
    *   If the condition is met, populate and return a `Signal` object. Otherwise, return `None`.
*   **Status:** Complete

---

### Task 5 — The Guardrail Gauntlet: Validation Service

*   **Rationale:** This is the most critical part of the system. A preliminary signal means nothing until it has survived our gauntlet of statistical and contextual checks. This service acts as the primary capital preservation mechanism.
*   **Items to implement:**
    *   Implement `services/validation_service.py` with a `ValidationService` class.
    *   Create private helper methods for each "guard" (`liquidity`, `market_regime`, `statistical_validity`).
    *   Implement a public `validate(df)` method that calls these checks sequentially.
*   **Status:** Complete. **Resolution**: The initial monolithic service was refactored into modular `Guard` classes as specified in the architecture document, improving maintainability.

---

## Epic 3: The Grinder - Realistic Backtesting

*Goal: To build a brutally realistic, cost-aware backtesting framework. The purpose of a backtest is not to produce a beautiful equity curve, but to see if a strategy can survive real-world frictions. Gross returns are a fantasy.*

---

### Task 6 — Execution Simulator with Indian Cost Model

*   **Rationale:** A trade is not just an entry and an exit; it's a series of transactions that incur costs. This component will simulate a single trade with a painfully realistic model of Indian market costs.
*   **Items to implement:**
    *   In `core/models.py`, define a `Trade` model.
    *   Implement `services/execution_simulator.py` with an `ExecutionSimulator` class.
    *   Implement a `simulate_trade` method that applies the full cost model (brokerage, STT, slippage).
*   **Status:** Complete. **Resolution**: The cost model was corrected to use the tiered slippage model from the architecture document. Logic was also added to handle zero-volume scenarios gracefully.

---

### Task 7 — Walk-Forward Backtesting Orchestrator

*   **Rationale:** To tie all the components together into a scientifically valid backtesting loop. We use a walk-forward approach to mitigate lookahead bias and simulate how the strategy would have performed in real time.
*   **Items to implement:**
    *   Implement `core/orchestrator.py` with an `Orchestrator` class.
    *   Implement the `run_backtest(stock)` method that correctly implements the walk-forward loop.
    *   Integrate all services (`DataService`, `SignalEngine`, `ValidationService`, `ExecutionSimulator`, `LLMAuditService`).
*   **Status:** Complete. **Resolution**: Critical data leakage issues were fixed, and the orchestrator was updated to efficiently calculate historical performance for the LLM audit service.

---

## Epic 4: The Auditor & The Output

*Goal: To integrate the LLM as a final statistical auditor and to produce the clear, actionable reports that are the system's final output.*

---

### Task 8 — LLM Audit Service with OpenRouter

*   **Rationale:** To integrate the LLM in its narrowly defined role: a statistical auditor. This service will be responsible for all communication with the LLM, strictly enforcing the "no price data" rule.
*   **Items to implement:**
    *   Implement `services/llm_audit_service.py` with an `LLMAuditService` class.
    *   The `get_confidence_score` method must query the LLM with a statistics-only prompt.
    *   It must robustly parse the LLM's response.
*   **Status:** Complete. **Resolution**: A critical performance issue was resolved by removing the "mini-backtest" logic from this service. The service is now a lean, stateless utility that relies on the Orchestrator to provide historical context, as per the architecture.

---

### Task 9 & 11 — Final Report Generation & CLI

*   **Rationale:** To synthesize the results and expose the system's functionality through a clean command-line interface.
*   **Items to implement:**
    *   Implement `services/report_generator.py`.
    *   Implement `generate_backtest_report` and `generate_opportunities_report` methods.
    *   Expand the Typer CLI in `main.py` with `backtest` and `generate-report` commands.
*   **Status:** Complete. **Resolution**: The `generate-report` command was previously incorrect and inefficient. It has been refactored to be correct and consistent with the backtesting logic. The CLI is now robustly accessible via a poetry script entry point.


### Task 11 — Implement Dynamic, Volatility-Based Exits

*   **Rationale:** The current fixed 20-day exit is a blunt, arbitrary instrument. It's a magic number that ignores the single most important variable after a trade is entered: volatility. A strategy cannot be considered robust if its exit logic is static while the market is dynamic. This task replaces the fixed exit with a data-driven one based on the stock's own recent volatility (ATR), making our risk management adaptive and provably linked to market conditions. This directly addresses a key future enhancement noted in the PRD.
*   **Items to implement:**
    1.  In `core/indicators.py`, add a new function `atr(high_series, low_series, close_series, length)` to calculate the Average True Range.
    2.  In `config.ini`, add a new `[exit_logic]` section. Include parameters like `use_atr_exit = True`, `atr_period = 14`, `atr_stop_loss_multiplier = 2.5`, and `max_holding_days = 40`.
    3.  In `core/models.py`, add a corresponding `ExitLogicConfig` Pydantic model and integrate it into the main `Config` model.
    4.  Modify the `Orchestrator.run_backtest` loop. The current logic that determines the exit (`exit_date_target_index = i + signal.exit_target_days`) must be replaced.
    5.  After a trade is initiated at index `i`, the orchestrator must now loop forward day-by-day (up to `max_holding_days`).
    6.  In this new inner loop, it will calculate the ATR-based trailing stop-loss for each day. The exit is triggered on the first day the low price breaches the stop-loss.
    7.  The orchestrator will pass the determined `exit_date_actual` and `exit_price` to the `ExecutionSimulator`, whose interface will not need to change, thus preserving architectural boundaries.
*   **Tests to cover:**
    *   Add a test to `tests/test_indicators.py` for the new `atr` function, validating its output against a known result.
    *   In `tests/test_orchestrator.py`, create a new integration test with a synthetic DataFrame where the price clearly hits a pre-calculated ATR stop-loss. Assert that the trade exits on the correct day and at the correct price.
    *   Create another test where the price meanders and never hits the stop-loss. Assert that it exits on the `max_holding_days` timeout.
*   **Acceptance Criteria (AC):**
    *   The backtester can be configured via `config.ini` to use either the legacy fixed-day exit or the new ATR-based exit.
    *   When the ATR exit is enabled, trades correctly exit based on hitting the trailing stop-loss or the max holding period.
*   **Definition of Done (DoD):**
    *   All new code is implemented, unit-tested, and integrated into the orchestrator. The `config.ini` is updated with the new section and documentation.
*   **Time estimate:** 6 hours
*   **Status:** Done