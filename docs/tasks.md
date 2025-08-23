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
    *   Create `requirements.txt` with initial dependencies: `pandas`, `numpy`, `statsmodels`, `yfinance`, `pydantic`, `python-dotenv`, `configparser`, `typer`, `pytest`, `mypy`.
    *   Create `config.ini` with sections for `[data]`, `[strategy_params]`, `[filters]`, and `[llm]`. Populate with all thresholds from the PRD (e.g., `sector_vol_threshold = 22.0`, `liquidity_turnover_crores = 5.0`).
    *   Implement `services/config_service.py` to load and parse `config.ini`.
    *   Implement `core/models.py` with a Pydantic `Config` model that provides type-safe access to all configuration values.
    *   Create the CLI entry point `main.py` using `Typer` with a placeholder command that loads the config and prints it.
*   **Tests to cover:**
    *   Create `tests/test_config_service.py`.
    *   Test that the service correctly parses a valid `config.ini` into the Pydantic model.
    *   Test that it raises a validation error for missing required keys or incorrect types.
*   **Acceptance Criteria (AC):**
    *   The project structure matches `architecture.md`.
    *   Running `mypy .` passes with zero errors.
    *   Running `python main.py` successfully loads and validates the configuration.
*   **Definition of Done (DoD):**
    *   The initial project structure and configuration service are committed.
*   **Time estimate:** 3 hours
*   **Status:** Not Started

---
### Task 1.1 — Fix Typer CLI Invocation

*   **Rationale:** The Typer CLI is not working as expected. This needs to be fixed to ensure the CLI is usable.
*   **Items to implement:**
    *   Investigate the `Typer` invocation issue mentioned in `docs/memory.md`.
    *   Fix the issue and ensure that `python -m praxis_engine.main verify-config` works as expected.
*   **Tests to cover:**
    *   N/A
*   **Acceptance Criteria (AC):**
    *   The Typer CLI can be invoked correctly.
*   **Definition of Done (DoD):**
    *   The Typer CLI invocation issue is resolved.
*   **Time estimate:** 1 hour
*   **Status:** Not Started
---

### Task 2 — Data Service for Indian Markets

*   **Rationale:** Data is the lifeblood. This service must be robust, efficient, and acutely aware of Indian market specifics. We will use the correct data sources and implement caching to make research fast and reproducible.
*   **Items to implement:**
    *   Add `yfinance` and `pyarrow` to `requirements.txt`.
    *   Implement `services/data_service.py` with a `DataService` class.
    *   The `get_data(stock, start_date, end_date)` method must:
        1.  Construct a cache filename (e.g., `HDFCBANK_2010-01-01_2023-12-31.parquet`).
        2.  If the cache file exists, load and return the DataFrame from it.
        3.  If not, fetch equity data using `yfinance.download`.
        4.  Fetch the corresponding Nifty sector index data using `yfinance`. A mapping from stock to sector index will be needed in `config.ini`.
        5.  Calculate the 20-day rolling annualized `sector_vol` and merge it into the main DataFrame.
        6.  Perform basic cleaning (e.g., forward-fill missing values, ensure date index is correct).
        7.  Save the final, clean DataFrame to the Parquet cache file.
*   **Tests to cover:**
    *   Create `tests/test_data_service.py`.
    *   Mock `yf.download` to test the caching logic without network calls.
    *   Verify that the `sector_vol` column is correctly calculated and merged.
*   **Acceptance Criteria (AC):**
    *   The `DataService` can download, process, and save data for a given stock.
    *   Subsequent calls for the same stock and date range use the cache.
*   **Definition of Done (DoD):**
    *   `data_service.py` and its unit tests are implemented and pass.
*   **Time estimate:** 3.5 hours
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
*   **Tests to cover:**
    *   Create `tests/test_indicators.py` and `tests/test_statistics.py`.
    *   For each function, create a test with a known input `pandas.Series` and assert that the output matches a pre-calculated, expected value. This validates our implementation against a known benchmark.
*   **Acceptance Criteria (AC):**
    *   All indicator and statistical functions are implemented.
    *   Each function has a unit test that validates its correctness against a known result.
*   **Definition of Done (DoD):**
    *   The indicator and statistics modules and their tests are implemented and committed.
*   **Time estimate:** 3 hours
*   **Status:** Not Started

---

## Epic 2: The Filtering Cascade - Signal & Validation

*Goal: To codify the core logic of the system. This involves translating the multi-frame signal generation rules and the non-negotiable statistical and contextual guardrails into deterministic code. This is where the "edge" is built.*

---

### Task 4 — Multi-Frame Signal Engine

*   **Rationale:** A simple BB+RSI signal is noise. The PRD specifies that the edge comes from multi-frame alignment. This engine will implement that precise logic to generate preliminary signals.
*   **Items to implement:**
    *   In `core/models.py`, define a Pydantic `Signal` model to hold entry price, stop-loss, and other relevant signal data.
    *   Implement `services/signal_engine.py` with a `SignalEngine` class.
    *   The `generate_signal(df_daily)` method must:
        1.  Calculate daily BBands and RSI using the functions from `core/indicators.py`.
        2.  Resample the daily data to weekly (`'W'`) and monthly (`'M'`) timeframes.
        3.  Calculate indicators on these resampled frames with the parameters specified in `project_brief.md` (e.g., weekly BB(10, 2.5)).
        4.  Implement the **exact** multi-frame alignment check from the brief: `daily_oversold AND weekly_oversold AND monthly_not_oversold`.
        5.  If the condition is met, populate and return a `Signal` object. Otherwise, return `None`.
*   **Tests to cover:**
    *   Create `tests/test_signal_engine.py`.
    *   Create a synthetic DataFrame where the alignment condition is met on the last day and assert that a `Signal` object is returned.
    *   Create several other synthetic DataFrames where one or more conditions fail and assert that `None` is returned.
*   **Acceptance Criteria (AC):**
    *   The engine correctly identifies the specific multi-frame alignment condition.
    *   It produces a structured `Signal` object only when all conditions are met.
*   **Definition of Done (DoD):**
    *   `signal_engine.py` and its tests are implemented and committed.
*   **Time estimate:** 4 hours
*   **Status:** Not Started

---

### Task 5 — The Guardrail Gauntlet: Validation Service

*   **Rationale:** This is the most critical part of the system. A preliminary signal means nothing until it has survived our gauntlet of statistical and contextual checks. This service acts as the primary capital preservation mechanism.
*   **Items to implement:**
    *   Implement `services/validation_service.py` with a `ValidationService` class.
    *   Create private helper methods for each "guard":
        *   `_check_liquidity(df)`: Calculates 5-day average turnover (Volume * Close) and checks if it's above the `₹5 Crore` threshold from the config.
        *   `_check_market_regime(df)`: Checks if the latest `sector_vol` is below the `22%` threshold.
        *   `_check_statistical_validity(df)`: Runs the `adf_test` and `hurst_exponent` functions on the price series and checks if `p_value < 0.05` and `H < 0.45`.
    *   Implement a public `validate(df)` method that calls these checks sequentially. If any check fails, it must immediately return `False` with a reason string (e.g., `"REJECTED: Low Liquidity"`). If all pass, it returns `True`.
*   **Tests to cover:**
    *   Create `tests/test_validation_service.py`.
    *   Test each failure case in isolation: create a DataFrame that is illiquid but otherwise fine; one with high sector volatility; one that is not mean-reverting. Assert that `validate` returns `False` with the correct reason.
    *   Test the success case: create a DataFrame that passes all checks and assert that `validate` returns `True`.
*   **Acceptance Criteria (AC):**
    *   The service correctly applies all filters defined in the PRD.
    *   The service rejects signals as soon as a single guardrail fails.
*   **Definition of Done (DoD):**
    *   `validation_service.py` and its comprehensive tests are implemented.
*   **Time estimate:** 4 hours
*   **Status:** Not Started

---

## Epic 3: The Grinder - Realistic Backtesting

*Goal: To build a brutally realistic, cost-aware backtesting framework. The purpose of a backtest is not to produce a beautiful equity curve, but to see if a strategy can survive real-world frictions. Gross returns are a fantasy.*

---

### Task 6 — Execution Simulator with Indian Cost Model

*   **Rationale:** A trade is not just an entry and an exit; it's a series of transactions that incur costs. This component will simulate a single trade with a painfully realistic model of Indian market costs.
*   **Items to implement:**
    *   In `core/models.py`, define a `Trade` model to store all details of a simulated trade: entry price, exit price, net return, costs, etc.
    *   Implement `services/execution_simulator.py` with an `ExecutionSimulator` class.
    *   Implement a `simulate_trade(df, signal, entry_index)` method that:
        1.  Determines the exit point (e.g., 20 days after `entry_index`).
        2.  Calculates the gross return.
        3.  Applies the cost model:
            *   Brokerage: `max(0.0003 * value, 20)` for both entry and exit.
            *   STT: `0.00025 * value`.
            *   Slippage: A function that returns a percentage based on the volume at `entry_index`.
        4.  Calculates the final **net return**.
        5.  Populates and returns a `Trade` object.
*   **Tests to cover:**
    *   Create `tests/test_execution_simulator.py`.
    *   Provide a sample trade scenario (entry price, exit price, volume) and assert that the calculated net return and individual cost components are correct down to the paisa.
*   **Acceptance Criteria (AC):**
    *   The simulator correctly calculates the net return after applying the full, multi-component Indian cost model.
*   **Definition of Done (DoD):**
    *   `execution_simulator.py` and its validation tests are implemented.
*   **Time estimate:** 3 hours
*   **Status:** Not Started

---

### Task 7 — Walk-Forward Backtesting Orchestrator

*   **Rationale:** To tie all the components together into a scientifically valid backtesting loop. We use a walk-forward approach to mitigate lookahead bias and simulate how the strategy would have performed in real time.
*   **Items to implement:**
    *   Implement `core/orchestrator.py` with an `Orchestrator` class.
    *   Implement the `run_backtest(stock)` method that:
        1.  Calls `DataService` to get the full historical data for the stock.
        2.  Initializes an empty list to store `Trade` objects.
        3.  Loops through the data from day 200 to the end (the walk-forward loop).
        4.  In each iteration `i`, it creates a `window = df.iloc[0:i]`.
        5.  It calls `SignalEngine` on the `window`. If a signal is generated for day `i-1`:
        6.  It calls `ValidationService` on the `window`.
        7.  If validation passes, it calls `ExecutionSimulator` to simulate the trade starting at day `i`.
        8.  The resulting `Trade` object is appended to the results list.
        9.  After the loop, it returns the list of all executed trades.
*   **Tests to cover:**
    *   This is an integration test. Create `tests/test_orchestrator_backtest.py`.
    *   Mock all services. Create a small, predictable DataFrame. Assert that the services are called in the correct order and that a trade is only simulated when the mock `SignalEngine` and `ValidationService` both give a green light.
*   **Acceptance Criteria (AC):**
    *   The orchestrator correctly implements the walk-forward methodology.
    *   It correctly integrates the signal, validation, and execution components.
*   **Definition of Done (DoD):**
    *   The backtesting orchestration logic in `orchestrator.py` is implemented and tested.
*   **Time estimate:** 4 hours
*   **Status:** Not Started

---

## Epic 4: The Auditor & The Output

*Goal: To integrate the LLM as a final statistical auditor and to produce the clear, actionable reports that are the system's final output.*

---

### Task 8 — Local LLM Audit Service

*   **Rationale:** To integrate the LLM in its narrowly defined role: a statistical auditor. This service will be responsible for all communication with the local LLM, strictly enforcing the "no price data" rule.
*   **Items to implement:**
    *   Add `ollama` to `requirements.txt`.
    *   Create `prompts/statistical_auditor.txt` with the Jinja2 template for the prompt, as specified in the PRD.
    *   Implement `services/llm_audit_service.py` with an `LLMAuditService` class.
    *   The `get_confidence_score(df_window, signal)` method must:
        1.  Calculate the required historical statistics from the `df_window` (win rate, profit factor, sample size).
        2.  Render the prompt template with these statistics.
        3.  Call the local Ollama instance with the prompt.
        4.  Parse the response, ensuring it's a valid float between 0.0 and 1.0. Handle errors gracefully by returning 0.0 if the response is malformed.
*   **Tests to cover:**
    *   Create `tests/test_llm_audit_service.py`.
    *   Mock the `ollama.chat` client. Verify that the service constructs the correct prompt string from a sample data window.
    *   Test the response parsing for valid floats, invalid text, and out-of-range numbers.
*   **Acceptance Criteria (AC):**
    *   The service can query the local LLM with a correctly formatted, statistics-only prompt.
    *   It robustly handles and sanitizes the LLM's response.
*   **Definition of Done (DoD):**
    *   `llm_audit_service.py` and its tests are implemented.
*   **Time estimate:** 3.5 hours
*   **Status:** In-progress

---

### Task 9 — Final Report Generation & CLI

*   **Rationale:** To synthesize the results of a backtest or a live run into the final, human-readable reports and expose the system's functionality through a clean command-line interface.
*   **Items to implement:**
    *   Implement `services/report_generator.py` with a `ReportGenerator` class.
    *   Implement a `generate_backtest_report(trades: list[Trade])` method that:
        1.  Calculates all final KPIs from the list of trades (Net Annualized Return, Cost-Adjusted Sharpe, Profit Factor, Max Drawdown, etc.).
        2.  Formats these KPIs into a clean Markdown string.
    *   Implement a `generate_weekly_report(opportunities: list[dict])` method that creates the Markdown table from the PRD.
    *   In `main.py`, expand the Typer CLI:
        *   Create a `backtest` command that runs the `Orchestrator` over the full Nifty 500 list, aggregates all trades, and uses the `ReportGenerator` to save a `backtest_summary.md`.
        *   Create a `generate-report` command that runs the full logic on the latest data and generates the weekly opportunities report.
    *   Integrate the `LLMAuditService` into the `Orchestrator` as the final check before simulating a trade.
*   **Tests to cover:**
    *   Create `tests/test_report_generator.py`.
    *   Pass a sample list of `Trade` objects and verify the calculated KPIs are correct.
*   **Acceptance Criteria (AC):**
    *   Running `python main.py backtest` executes a full backtest and produces a summary report with all required KPIs.
    *   Running `python main.py generate-report` produces the weekly opportunities table.
    *   The LLM audit is correctly integrated as the final filter.
*   **Definition of Done (DoD):**
    *   The reporting services and the final user-facing CLI are complete and functional.
*   **Time estimate:** 4 hours
*   **Status:** Not Started