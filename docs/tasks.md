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
*   **Status:** Complete. 
---

### Task 1.2 — Solidify Project Dependencies
*   **Rationale:** The project is missing a formal dependency management file (e.g., `requirements.txt`). Several libraries (`typer`, `pyarrow`, `openai`, etc.) were required to run the backtest but were not installed as part of the initial setup, causing runtime errors. This makes the project difficult to set up and violates the principle of a reproducible environment.
*   **Items to implement:**
    1.  Create a `requirements.txt` file that lists all necessary dependencies for running the application and the tests.
    2.  Update the `README.md` or a new `CONTRIBUTING.md` with clear instructions on how to set up the development environment using `pip install -r requirements.txt`.
    3.  Ensure all required packages are included so that a fresh checkout can be run with a single installation command.
*   **Status:** Done. **Resolution**: A `requirements.txt` file has been created at the project root, establishing a single source of truth for all runtime and development dependencies. This resolves the dependency management issues noted in `docs/memory.md`. The project can now be set up with a single command (`pip install -r requirements.txt`).

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
*   **Status:** Complete. **Resolution**: A critical performance issue was resolved by removing the "mini-backtest" logic from this service. The service is now a lean, stateless utility that relies on the Orchestrator to provide historical context, as per the architecture. The service was further hardened to handle multiple LLM providers (`OpenAI`, `OpenRouter`) controlled via environment variables. Test coverage was increased to >90% to cover initialization failures, API errors, and other edge cases. The default behavior for unconfigured providers was changed to be fail-safe (return 0.0 score).

---

### Task 9 — Final Report Generation & CLI

*   **Rationale:** To synthesize the results and expose the system's functionality through a clean command-line interface.
*   **Items to implement:**
    *   Implement `services/report_generator.py`.
    *   Implement `generate_backtest_report` and `generate_opportunities_report` methods.
    *   Expand the Typer CLI in `main.py` with `backtest` and `generate-report` commands.
*   **Status:** Complete. **Resolution**: The `generate-report` command was previously incorrect and inefficient. It has been refactored to be correct and consistent with the backtesting logic. The CLI is now robustly accessible via a poetry script entry point.

### Task 10 — Implement Dynamic, Volatility-Based Exits

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

---

## Epic 5: Critical Refactoring & Validation

*Goal: To correct severe architectural flaws, data leakage, and inefficiencies discovered during a full-code review. These fixes are non-negotiable for the system to produce scientifically valid results.*

### Task 11 — Fix Lookahead Bias and Orchestrator Logic

*   **Rationale:** A full code review uncovered critical flaws that invalidated backtest results. The `Orchestrator` contained lookahead bias in its ATR calculation and had a catastrophically inefficient `generate_opportunities` method. This task corrects these core architectural problems to restore experimental integrity.
*   **Items to implement:**
    1.  **Fix ATR Lookahead Bias:** Move the ATR calculation from a pre-computation step on the full dataset to *inside* the `run_backtest` walk-forward loop. The ATR must be calculated only on the point-in-time `window` dataframe at each step.
    2.  **Refactor `generate_opportunities`:** The existing method, which ran a full backtest for every stock, was deleted. It has been replaced with a new, efficient implementation that:
        a. Checks for a signal and validates it only on the most recent data point.
        b. If the signal is valid, it calls a new helper method (`_calculate_historical_stats_for_llm`) to perform a lean, focused backtest on the data *prior* to the signal date.
        c. This provides the necessary historical context to the LLM without re-running the main backtester.
*   **Status:** Done


### Task 12 — Implement Systematic Parameter Sensitivity Analysis

*   **Rationale:** Blindly changing parameters in `config.ini` to find a better result is unscientific, inefficient, and prone to overfitting. This task introduces a systematic, reproducible framework to explore the parameter space. It transforms parameter tuning from guesswork into a controlled experiment, providing the data needed to make informed decisions about the system's risk/reward profile. This is fundamental to understanding the model's behavior and the true drivers of its performance (or lack thereof).
*   **Items to implement:**
    1.  In `config.ini`, add a new `[sensitivity_analysis]` section. This section will define the parameter to vary (e.g., `parameter_to_vary = "filters.sector_vol_threshold"`), a start value, an end value, and a step size.
    2.  In `run.py` and `praxis_engine/main.py`, add a new CLI command: `sensitivity-analysis`.
    3.  Create a new method in `core/orchestrator.py` called `run_sensitivity_analysis()`. This method will:
        a. Read the analysis parameters from the config.
        b. Loop through the specified range of values for the target parameter.
        c. In each iteration, create a *deep copy* of the main `Config` object and dynamically update the single parameter being tested. This is critical to ensure runs are isolated and the base configuration remains immutable.
        d. Run the full backtest across all configured stocks using this temporary, modified config.
        e. Store the aggregated KPIs (Sharpe, Profit Factor, Total Trades, etc.) for each parameter value.
    4.  In `services/report_generator.py`, add a new method `generate_sensitivity_report()`. This method will take the results from the analysis and format them into a clear Markdown table showing how performance metrics change as the parameter changes.
    5.  The `sensitivity-analysis` command will call the orchestrator and then the report generator, saving the final output to `results/sensitivity_analysis_report.md`.
*   **Tests to cover:**
    *   This is a high-level integration test. In a new `tests/test_orchestrator_analysis.py`, mock the `run_backtest` method.
    *   Call `run_sensitivity_analysis` and assert that `run_backtest` is called the correct number of times, corresponding to the steps in the parameter range.
    *   Crucially, assert that the `Config` object passed to the services during each mocked run contains the correctly modified parameter value for that specific iteration.
    *   In `tests/test_report_generator.py`, add a test for `generate_sensitivity_report` to verify the correct formatting of the output table.
*   **Acceptance Criteria (AC):**
    *   A new CLI command `praxis sensitivity-analysis` is available.
    *   Running the command executes multiple backtests as defined in the `[sensitivity_analysis]` section of `config.ini`.
    *   A Markdown report is generated in the `results/` directory that clearly tabulates the system's performance KPIs against each tested parameter value.
*   **Definition of Done (DoD):**
    *   All new code for the CLI, orchestrator, and report generator is implemented, unit-tested, and documented. The `config.ini` is updated with a documented example of the new section.
*   **Time estimate:** 8 hours
*   **Status:** Done

---

## Epic 6: Transition to Probabilistic Filtering

*Goal: To evolve the system from a rigid, binary filtering cascade into a more nuanced, probabilistic model. This involves refactoring the guards to produce continuous scores instead of true/false verdicts and empowering the LLM to weigh these scores as part of its final audit. This directly addresses the core issue of hyper-selectivity by allowing the system to evaluate signals on a spectrum of quality rather than a simple pass/fail basis.*

---

### Task 13 — Refactor Guards from Binary to Probabilistic Scoring

*   **Rationale:** The current `True/False` validation from the guards is a primary cause of the low trade count. A signal where the Hurst exponent is `0.451` is discarded as readily as one where it is `0.80`. This throws away valuable information. Refactoring the guards to return a continuous score (0.0 to 1.0) will allow the system to understand nuance—that a signal can be "weak but acceptable" in one dimension if it is "excellent" in others.
*   **Items to implement:**
    1.  **Models:** In `core/models.py`, create a new Pydantic model `ValidationScores(BaseModel)` with fields: `liquidity_score: float`, `regime_score: float`, `stat_score: float`. The existing `ValidationResult` model will be deprecated and removed.
    2.  **Guard Interface:** The `GuardProtocol` in `services/validation_service.py` must be updated. The `validate` method will now return a single `float` score.
    3.  **Guard Implementations:** Each guard's `validate` method must be rewritten to return a score instead of a `ValidationResult`.
        *   `LiquidityGuard`: Implement a linear scoring function. A turnover of `0.5 * threshold` might score `0.0`, while `2.0 * threshold` scores `1.0`.
        *   `RegimeGuard`: Implement a linear scoring function for sector volatility. A vol of `25%` might score `0.0`, while `10%` scores `1.0`.
        *   `StatGuard`: Calculate separate scores for the ADF p-value and the Hurst exponent, then return the geometric mean of the two scores.
    4.  **Validation Service:** The `ValidationService.validate` method must be completely refactored. It will no longer short-circuit. It must:
        a. Call every guard in its list.
        b. Collect the score from each guard.
        c. Return a populated `ValidationScores` object.
    5.  **Configuration:** Add new parameters to `config.ini` under a `[scoring]` section to control the boundaries of these new linear scoring functions (e.g., `hurst_score_min = 0.55`, `hurst_score_max = 0.3`).
*   **Tests to cover:**
    *   Update all tests in `tests/test_validation_service.py` to reflect the new return types and logic.
    *   Add specific tests for each guard's scoring function. For example, create a test for `StatGuard` with a known Hurst value and assert that the returned score is mathematically correct based on the configured boundaries.
*   **Acceptance Criteria (AC):**
    *   All guards return a float score between 0.0 and 1.0.
    *   The `ValidationService` successfully aggregates these scores into a `ValidationScores` object.
*   **Definition of Done (DoD):**
    *   All code is refactored, all new configuration is added, and all associated unit tests are updated and passing.
*   **Time estimate:** 8 hours
*   **Status:** Done

---

### Task 14 — Empower LLM with Guard Scores for Nuanced Auditing

*   **Rationale:** With the guards now producing rich, probabilistic data, the final step is to feed this information to the LLM. This completes the architectural vision of the LLM as a sophisticated, non-linear function that weighs multiple, continuous inputs to make a final judgment, moving it beyond the limitations of the original, statistics-only prompt.
*   **Items to implement:**
    1.  **Prompt Engineering:** Modify the `praxis_engine/prompts/statistical_auditor.txt` template. Add a new section for the guard scores, clearly labeling each one (e.g., `- Current Signal Quality - Liquidity Score: {{ liquidity_score }}`, `- Regime Score: {{ regime_score }}`, `- Statistical Score: {{ stat_score }}`).
    2.  **LLM Audit Service:** The `get_confidence_score` method in `services/llm_audit_service.py` must be updated. Its signature will now accept the `ValidationScores` object as an argument. The context dictionary passed to the Jinja2 template must be updated to include these new scores.
    3.  **Orchestrator Integration:** In `core/orchestrator.py`, update the main backtest loop. The call to `validation_service.validate()` will now return a `ValidationScores` object. This object must be passed directly to the subsequent call to `llm_audit_service.get_confidence_score()`.
    4.  **Orchestrator Pre-filter:** Add a simple pre-filter in the `Orchestrator` after the validation step. If the product of the scores (`liquidity * regime * stat`) is below a new, very low threshold in `config.ini` (e.g., `min_composite_score_for_llm = 0.05`), skip the LLM call to save resources on obviously terrible signals.
*   **Tests to cover:**
    *   In `tests/test_llm_audit_service.py`, update the `get_confidence_score` test. It should now pass a mock `ValidationScores` object. The core assertion will be to check that the rendered prompt string correctly includes the formatted scores.
    *   Update the integration tests in `tests/test_orchestrator.py` to mock the new return value from the `ValidationService` and assert that it is passed correctly to the `LLMAuditService`.
*   **Acceptance Criteria (AC):**
    *   The backtest log shows the new, expanded LLM prompt containing the guard scores.
    *   The system completes a full backtest run using the new end-to-end data flow.
*   **Definition of Done (DoD):**
    *   All code changes are implemented, the prompt is updated, and all relevant unit and integration tests are passing.
*   **Time estimate:** 4 hours
*   **Status:** Done

---

### Task 15 — Enhance Backtest User Experience

*   **Rationale:** The backtest output is verbose and hard to follow. A progress bar and per-stock summaries will make the backtesting process more user-friendly and provide immediate feedback on the performance of the strategy for each stock. The detailed logs will be moved to a file for later analysis.
*   **Items to implement:**
    1.  **File Logging:** Configure the logger to write detailed `DEBUG` level logs to `results/backtest_results.log`. The console logger should only show `INFO` level messages.
    2.  **Progress Bar:** Use `tqdm` to display a progress bar for the backtesting loop over the stocks.
    3.  **Per-Stock Summary:** After each stock is backtested, generate and print a summary of the results to the console.
    4.  **Less Verbose Orchestrator:** Change verbose `log.info` statements in the `Orchestrator` to `log.debug` to keep the console output clean.
*   **Status:** Done

## Epic 7: From Output to Insight - Advanced Diagnostics & Reporting

*Goal: To transform the backtest output from a simple KPI summary into a comprehensive diagnostic tool. This is not about changing the core strategy logic, but about instrumenting it to provide the deep, analytical insights required to improve it scientifically. A backtest that only tells you the final P/L is a missed opportunity; a backtest that tells you *why* you achieved that P/L is the foundation for progress. We will make our system's thinking transparent and auditable.*

---

### Task 16 — Instrument Backtest Runs with Reproducibility Metadata

*   **Rationale:** A backtest is a scientific experiment. An experiment without documented initial conditions is unreproducible and therefore invalid. This task ensures that every report is stamped with the exact context in which it was generated, adhering to `[H-23]`.
*   **Items to implement:**
    1.  **Git Hash:** Create a utility function (e.g., in a new `praxis_engine/utils.py`) that uses the `subprocess` module to execute `git rev-parse --short HEAD` and retrieve the current commit hash. This function must handle cases where Git is not installed or it's not a Git repository.
    2.  **Orchestrator:** The `Orchestrator` must gather the run timestamp, the path to the config file, and the Git hash at the beginning of a run.
    3.  **Report Generator:** The `generate_backtest_report` method in `services/report_generator.py` must be updated to accept this metadata.
    4.  **Output:** Add a new "Run Configuration & Metadata" section to the top of `backtest_summary.md` that displays this information in a clean Markdown table.
*   **Tests to cover:**
    *   A unit test for the new Git hash utility function, mocking the `subprocess.run` call.
    *   Update `tests/test_report_generator.py` to check that the metadata section is correctly rendered in the output string.
*   **Status:** Done

---

### Task 17 — Implement Signal Attrition Funnel and Guardrail Rejection Tracking

*   **Rationale:** The system's primary function is to filter. We are blind to its effectiveness if we don't measure what it filters. This task instruments the entire decision-making pipeline to produce a "funnel," showing exactly how many signals are discarded at each stage and, crucially, *why*. This is the most direct way to identify which guardrail is doing the most work, per `[The Nadh Principle]` of pragmatic simplicity.
*   **Items to implement:**
    1.  **Orchestrator State:** Modify the `Orchestrator`'s main `backtest` loop in `praxis_engine/main.py`. It must now maintain counters for: `potential_signals`, `rejections_by_guard`, `rejections_by_llm`, and `trades_executed`. The `rejections_by_guard` should be a dictionary counting rejections per guard type (e.g., `{'StatGuard': 0, 'RegimeGuard': 0}`).
    2.  **Rejection Logic:** In `core/orchestrator.py`, after `validation_service.validate()` returns the `ValidationScores`, if the composite score is below the `min_composite_score_for_llm` threshold, determine the primary reason for rejection by finding which score (`liquidity`, `regime`, or `stat`) was the lowest. Increment the corresponding counter.
    3.  **Data Aggregation:** The main loop must aggregate these counts across all stocks.
    4.  **Report Generator:** Create new methods in `services/report_generator.py` to generate the "Filtering Funnel" and "Guardrail Rejection Analysis" tables from the aggregated counter data.
*   **Tests to cover:**
    *   In `tests/test_orchestrator.py`, create a new test that mocks the return values of the services to simulate a flow where signals are rejected by different guards. Assert that the final counts returned by the orchestrator are correct.
    *   In `tests/test_report_generator.py`, add tests for the new funnel and rejection table generation methods.
*   **Status:** Done
*   **Resolution:** The signal attrition funnel and rejection tracking have been fully implemented in the Orchestrator and Report Generator. The logic correctly tracks potential signals and their rejections at both the guardrail and LLM audit stages. Unit and integration tests have been added to verify this functionality. It was observed during testing that the current strategy configuration is highly restrictive and results in zero trades, which the system now correctly reports. The implementation is sound; tuning the strategy parameters is a separate task.

---

### Task 18 — Add Per-Stock Performance Breakdown

*   **Rationale:** System-wide averages are deceptive; they hide excellence and mediocrity. A strategy might be brilliant on 5 stocks and terrible on 20. This task provides the granular, per-stock data needed to understand where the strategy actually works, enabling intelligent pruning of the stock universe.
*   **Items to implement:**
    1.  **Orchestrator Return Value:** The `Orchestrator.run_backtest` method must be refactored. Instead of just returning a list of trades, it should return a dictionary or a data class containing the trades for that stock *and* the rejection counts for that stock.
    2.  **CLI Aggregation:** The `backtest` command in `praxis_engine/main.py` must be updated to handle this new return type. It will aggregate the per-stock results into a master data structure (e.g., a dictionary keyed by stock symbol).
    3.  **Report Generator:** Add a new method `generate_per_stock_report` to `services/report_generator.py`. This method will take the aggregated per-stock data and format it into the specified Markdown table, including trade counts, P/L, and rejection statistics for each stock.
*   **Tests to cover:**
    *   Update tests in `tests/test_orchestrator.py` to reflect the new return signature of `run_backtest`.
    *   Add a new test in `tests/test_report_generator.py` to verify the correct formatting of the per-stock table.
*   **Status:** Done

---

### Task 19 — Implement Trade Distribution and Statistical Analysis

*   **Rationale:** To move beyond simple averages and understand the *character* of the strategy's returns, per the Hinton mindset. A strategy with a positive average return driven by one massive outlier is fundamentally different and riskier than one with consistent small gains. This task adds the statistical measures (skew, kurtosis) and visualizations needed to see the true shape of the P/L distribution.
*   **Items to implement:**
    1.  **Pandas Dependency:** Ensure `pandas` is used for statistical calculations to avoid adding new dependencies like `scipy`, adhering to `[H-8]`.
    2.  **Report Generator:** In `services/report_generator.py`, enhance the `_calculate_kpis` method (or create a new one) to compute:
        *   Average Win %, Average Loss %
        *   Best Trade %, Worst Trade %
        *   Average Holding Period in days.
        *   Skewness and Kurtosis of the net return series (`pd.Series(returns).skew()`, `.kurt()`).
    3.  **ASCII Histogram:** Create a new, pure utility function (e.g., in `praxis_engine/utils.py`) called `generate_ascii_histogram(data: List[float]) -> str`. This function will bin the returns and generate a simple text-based histogram.
    4.  **Output:** Integrate the new table and the histogram into the `backtest_summary.md` output.
*   **Tests to cover:**
    *   A unit test for the `generate_ascii_histogram` utility with a known data set to verify the output format.
    *   Update `tests/test_report_generator.py` to assert that the new distribution table and histogram are present and correctly formatted in the final report string.
*   **Status:** Done

---

### Task 20 — Implement LLM Performance Uplift Analysis

*   **Rationale:** The LLM is the most expensive and opaque component of the system. Its value cannot be assumed; it must be rigorously quantified. This task implements a baseline comparison to measure the LLM's direct contribution (or harm) to the strategy's performance, adhering to Hinton's principle of isolating and measuring the impact of intelligent components (`[H-26]`).
*   **Items to implement:**
    1.  **Orchestrator Logic Change:** This is a critical refactoring of `core/orchestrator.py`.
        a. After a signal passes the guardrail pre-filter, the `Orchestrator` must immediately simulate the trade as if it were to be executed. This trade object is stored in a new list, `pre_llm_trades`.
        b. *Then*, the signal is sent to the `LLMAuditService`.
        c. If the LLM confidence score is sufficient, the *exact same trade object* is also appended to the final `trades` list.
        d. The `run_backtest` method must now return both lists: `pre_llm_trades` and `final_trades`.
    2.  **LLM Score Logging:** The `Orchestrator` must collect every confidence score returned by the `LLMAuditService` throughout the backtest into a list.
    3.  **Report Generator:** Create a new method `generate_llm_uplift_report`. It will:
        a. Accept the `pre_llm_trades` and `final_trades` lists.
        b. Calculate KPIs for both sets of trades.
        c. Compute the percentage uplift (or decline) for key metrics like Profit Factor and Win Rate.
        d. Use the `generate_ascii_histogram` utility to create a distribution chart of the collected LLM scores.
        e. Format all of this into the "LLM Audit Performance Analysis" section.
*   **Tests to cover:**
    *   This requires a significant update to `tests/test_orchestrator.py`. Create a new integration test that simulates a scenario where some signals pass the guards but are then rejected by the LLM. Assert that `run_backtest` returns two lists of trades with the correct contents.
    *   Add a new test to `tests/test_report_generator.py` for `generate_llm_uplift_report`, providing it with two mock lists of trades and asserting the final table and uplift calculations are correct.
*   **Status:** Done

---
### Task 21 — Align Task Numbers with Descriptions
*   **Rationale:** There is a discrepancy between user requests for specific task numbers (e.g., "Task 17") and the content of those tasks in this document. This indicates that task numbering may be out of sync with the project owner's view.
*   **Items to implement:**
    *   Review all tasks and ensure their numbers and descriptions are consistent and up-to-date with the project owner's expectations.
    *   This is a documentation and project management task.
*   **Status:** Done


---

### Task 22 — Harden LLM API Connectivity

*   **Rationale:** The backtest runs are consistently failing with `APIConnectionError` when trying to reach the OpenRouter service. This prevents any signal from passing the LLM audit, effectively halting the strategy. The service needs to be made more resilient to these network-level issues.
*   **Items to implement:**
    1.  **Investigate Root Cause:** Determine if the `APIConnectionError` is due to an invalid API key, a problem with the OpenRouter service itself, or a local network configuration issue.
    2.  **Implement Exponential Backoff:** Wrap the `llm_audit_service`'s API call in a retry loop with exponential backoff (e.g., using the `tenacity` library or a manual implementation) to handle transient network errors more gracefully.
    3.  **Add Timeout:** Configure a reasonable timeout for the API request to prevent the system from hanging indefinitely.
    4.  **Improve Error Logging:** Enhance the logging in `LLMAuditService` to provide more context when an API error occurs, including the number of retries attempted.
*   **Tests to cover:**
    *   Add a test to `tests/test_llm_audit_service.py` that mocks the API client to throw an `APIConnectionError` and asserts that the retry logic is triggered the correct number of times.
*   **Status:** Done

---
### Task 23 — Update PRD and other documentation
*   **Rationale:** The PRD and other documentation may be out of date with the current implementation. This task is to review and update the documentation to reflect the current state of the project.
*   **Items to implement:**
    *   Review `docs/prd.md` and update it to reflect the use of OpenRouter and the Kimi 2 model.
    *   Review `docs/memory.md` and add any new learnings.
    *   Review `README.md` and update if necessary.
*   **Status:** To Do

---

### Task 24 — Implement Dynamic Profit Target for Symmetrical Risk Management

*   **Rationale:** (Hinton) The backtest report shows a negative skew of -0.94. This is a statistical warning that our profit distribution has a longer tail on the left; our losses, when they occur, are more severe than our wins are beneficial. This creates a poor risk-adjusted return profile. (Nadh) Architecturally, our exit logic is asymmetrical and incomplete. We have a well-defined rule for when we are wrong (the ATR stop-loss) but no rule for when we are right. We are letting profitable trades run indefinitely until a timeout, which is arbitrary. This task introduces a symmetrical, data-driven profit target to test the hypothesis that systematically capturing gains will improve the Sharpe Ratio by shaping a more favorable return distribution.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, within the `[exit_logic]` section, add a new parameter: `reward_risk_ratio = 2.0`.
    2.  **Models:** In `core/models.py`, add the corresponding `reward_risk_ratio: float` field to the `ExitLogicConfig` Pydantic model.
    3.  **Orchestrator Logic:** Refactor the `Orchestrator._determine_exit` method in `core/orchestrator.py`.
        a. At the point of trade entry (at index `i`), calculate the risk distance: `risk_per_share = entry_price - stop_loss_price`.
        b. Calculate the profit target: `profit_target_price = entry_price + (risk_per_share * self.config.exit_logic.reward_risk_ratio)`.
        c. Inside the day-by-day forward loop that checks for the stop-loss, add a condition to check if the day's `High` price has crossed the `profit_target_price`.
        d. If the profit target is hit, the exit is triggered. The `exit_price` must be the `profit_target_price` itself (not the day's high) to ensure a conservative and deterministic exit simulation. This exit takes precedence over the max holding period.
*   **Time estimate:** 5 hours
*   **Status:** Done & Reverted

*   **Resolution & Learnings:**
    *   **Outcome:** The implementation was functionally correct, but the backtest revealed a catastrophic drop in all performance metrics (Sharpe Ratio, Annualized Returns, Profit Factor). The hypothesis that a symmetrical risk:reward target would improve performance was **conclusively falsified**.
    *   **Root Cause:** A fundamental mismatch between the strategy's nature and the exit logic was identified. Our system is a **mean-reversion** strategy that profits from short-term reversions to a statistical mean. The fixed reward:risk ratio is a **trend-following** exit concept. It forced the system to hold winning trades for too long, waiting for large, trend-like profit targets that rarely materialized, causing profitable trades to decay into smaller wins or even losses.
    *   **Final Action:** The changes from this task have been **reverted** from the codebase. The previous, simpler exit logic (ATR stop-loss or max holding period) proved more effective because it did not contradict the core statistical edge of the entry signal. A detailed post-mortem has been added to `docs/memory.md` to ensure this flawed approach is not attempted again.

---
### Task 25 — Create Universe Pre-Filtering Script for Strategy Specialization

*   **Rationale:** (Nadh) The backtest proved the strategy is a specialist. It works on `POWERGRID.NS` and fails everywhere else. Wasting CPU cycles backtesting a mean-reversion strategy on trending stocks like `RELIANCE.NS` is inefficient and violates the "fail fast" principle. The most pragmatic solution is not to change the algorithm, but to curate the universe it operates on. (Hinton) This is a form of dataset curation, a crucial step in any applied ML project. We are simplifying the problem for our model by pre-selecting a dataset where the signal-to-noise ratio for mean-reversion is inherently higher. This is valid, provided the selection is done on out-of-sample data to prevent selection bias from contaminating our final backtest results.
*   **Items to implement:**
    1.  **Create New Script:** Create a new, standalone script: `scripts/universe_analyzer.py`. This script will not be part of the main `praxis_engine` package.
    2.  **Script Logic:** The script should:
        a. Define a list of Nifty 500 tickers (this can be hardcoded or read from a simple text file).
        b. Define an out-of-sample date range for analysis (e.g., `2010-01-01` to `2017-12-31`), which does not overlap with the main backtest period.
        c. Loop through each stock ticker.
        d. Use the `DataService` to fetch historical data.
        e. Use the `hurst_exponent` function from `core/statistics.py` to calculate the Hurst exponent for the entire period.
        f. Store the results (ticker and Hurst value) in a list.
        g. After processing all stocks, sort the list by the Hurst exponent in ascending order.
        h. Print a clean, copy-paste-ready list of the top 50 tickers where `Hurst < 0.5`.
    3.  **Documentation:** Add a section to `README.md` explaining how to run this script to generate a curated stock list for `config.ini`.
*   **Tests to cover:**
    *   Given this is a one-off analysis script, a full test suite is over-engineering. The primary test is to run the script and manually verify that it produces a sensible, sorted list of tickers and their Hurst values.
*   **Acceptance Criteria (AC):**
    *   A new script exists that can analyze a list of stocks and identify the most mean-reverting candidates based on historical data.
    *   The output is a simple list of stock tickers that can be directly used to update the `stocks_to_backtest` parameter in `config.ini`.
*   **Definition of Done (DoD):**
    *   The script is created and functional. The `README.md` is updated with instructions for its use.
*   **Time estimate:** 3 hours
*   **Status:** Done

---
### Task 26 — Update Stock Universe with Curated List

*   **Rationale:** (Nadh) The `universe_analyzer.py` script (Task 25) was created to provide a data-driven list of mean-reverting stocks. The final step to operationalize this finding is to update the system's configuration to use this curated list. This ensures that the backtester's resources are focused only on the stocks where the strategy has the highest probability of being applicable, directly applying the key learning from previous, broader backtests.
*   **Items to implement:**
    1.  Run the `scripts/universe_analyzer.py` script to generate the list of mean-reverting tickers.
    2.  Copy the output list of tickers.
    3.  Open `config.ini` and replace the value of the `stocks_to_backtest` parameter in the `[data]` section with the new, curated list.
    4.  Run a full backtest using the `run.py backtest` command to confirm the system runs correctly with the new, specialized stock universe.
*   **Tests to cover:**
    *   The primary test is to run the backtester and ensure it completes without errors using the new stock list.
*   **Acceptance Criteria (AC):**
    *   The `config.ini` file is updated with a list of stocks identified as mean-reverting by the universe analyzer.
    *   A backtest run completes successfully using this new configuration.
*   **Definition of Done (DoD):**
    *   The `config.ini` file is updated and a successful backtest has been run.
*   **Time estimate:** 1 hour
*   **Status:** Done

---

## Epic 8: Performance & Scalability

*Goal: To transform the backtesting engine from a slow, single-threaded research tool into a high-performance system capable of rapidly analyzing hundreds of stocks. This epic addresses the critical performance bottlenecks identified in the initial implementation, making large-scale analysis and sensitivity testing feasible.*

---

### Task 27 — Parallelize Per-Stock Backtests with Multiprocessing

*   **Rationale:** (Nadh) The current single-threaded backtest is the most significant bottleneck for analyzing a large universe. The problem is "embarrassingly parallel," as each stock's backtest is independent. Leveraging all available CPU cores is the most pragmatic, highest return-on-investment change to achieve a near-linear speedup for the entire run without altering the core strategy logic.
*   **Items to implement:**
    1.  Modify the `backtest` command in `praxis_engine/main.py`.
    2.  Import Python's `multiprocessing.Pool`.
    3.  Create a top-level helper function that can be pickled by `multiprocessing`. This function will accept a stock ticker, create a new `Orchestrator` instance, and run the backtest for that single stock.
    4.  Replace the main `for` loop over the stock list with a call to `pool.imap_unordered` to distribute the work across all available CPU cores.
    5.  Integrate `tqdm` with the multiprocessing pool to ensure the progress bar continues to function correctly.
    6.  Collect the results from all parallel processes and run the existing aggregation and report generation logic.
*   **Tests to cover:**
    *   This is primarily a functional test. The key validation is to run a backtest on a small, fixed set of stocks (e.g., 4-8) both before and after the change on a multi-core machine.
    *   **Assertion 1:** The parallel version must complete significantly faster.
    *   **Assertion 2:** The final generated `backtest_summary.md` must be numerically identical to the one from the single-threaded run.
*   **Acceptance Criteria (AC):**
    *   The `backtest` command utilizes multiple CPU cores during execution.
    *   A full backtest on the configured universe completes in a fraction of the original time.
    *   The final aggregated report is identical to the one produced by a single-threaded run, ensuring correctness.
*   **Definition of Done (DoD):**
    *   The `main.py` backtest command is refactored to use `multiprocessing.Pool`. The system correctly utilizes parallel processing, and the results are verified to be correct.
*   **Time estimate:** 4 hours
*   **Status:** Done

---

### Task 28 — Accelerate Numerical Hotspots with Numba JIT

*   **Rationale:** (Hinton/Nadh) Profiling reveals that specific, pure-Python numerical functions, like the Hurst exponent calculation, are computational hotspots within each backtest. While vectorization is preferred, some algorithms are inherently loopy. Instead of a costly rewrite in C, we can use Numba to Just-In-Time (JIT) compile these critical Python functions into highly optimized machine code. This is a targeted, surgical optimization that provides C-like speed for the parts of the code that need it most.
*   **Items to implement:**
    1.  Add `numba` to the project's `requirements.txt`.
    2.  **Profile:** Use a profiler (e.g., `cProfile`) to confirm the primary numerical bottlenecks during a single-stock run. The `hurst_exponent` function in `core/statistics.py` is the primary suspect.
    3.  **Refactor for Numba:**
        a. In `core/statistics.py`, import `numba`.
        b. Decorate the `hurst_exponent` function (or another identified bottleneck) with `@numba.jit(nopython=True)`.
        c. Modify the function to work with NumPy arrays instead of Pandas Series. The calling code must be updated to pass `series.to_numpy()`.
        d. Ensure all code inside the decorated function is compatible with Numba's `nopython` mode, refactoring to basic loops or supported NumPy functions if necessary.
*   **Tests to cover:**
    *   The existing unit tests for `hurst_exponent` in `tests/test_statistics.py` must continue to pass, verifying the numerical correctness of the JIT-compiled version.
    *   (Optional but recommended) Add a benchmark test using `pytest-benchmark` to formally measure and assert the performance gain of the Numba-fied function against the original.
*   **Acceptance Criteria (AC):**
    *   At least one identified computational bottleneck is successfully accelerated with the `@numba.jit` decorator.
    *   The backtest produces identical numerical results (within a small tolerance for floating-point differences).
    *   The overall runtime for a single stock backtest is measurably reduced due to the optimization.
*   **Definition of Done (DoD):**
    *   The `numba` dependency is added. The target function is refactored, decorated, and fully tested for both correctness and performance improvement.
*   **Time estimate:** 6 hours
*   **Status:** Done